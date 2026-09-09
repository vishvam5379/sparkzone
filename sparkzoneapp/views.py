import os
import re
import json
import uuid
import hashlib
from datetime import datetime, timedelta, time
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection, transaction as db_transaction
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone

from .models import (
    User, ProviderProfile, UserProfile, Country, State, City,
    Category, Game, Slot, GameImages, Booking, Notification,
    Payment, Reviews, FavoriteVenue, ContactUs
)
from .services import (
    create_razorpay_order, verify_razorpay_signature, process_razorpay_refund, is_razorpay_live,
    send_booking_confirmation_sms, send_slot_reminder_sms, send_cancellation_sms,
    send_booking_confirmation_email, send_cancellation_email
)
from .consumers import broadcast_station_update

# ─── Auth Helpers & Role Decorators ───────────────────────────────────────────
def get_logged_in_user(request):
    uid = request.session.get('user_id')
    if uid:
        try:
            user = User.objects.select_related('provider_profile').get(id=uid)
            if request.session.get('role') != user.role:
                request.session['role'] = user.role
            return user
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('role', None)
    return None

def get_user_notifications(user):
    if not user:
        return [], 0
    notifs = Notification.objects.filter(user=user).order_by('-timestamp')[:10]
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    return notifs, unread_count

def mark_notifications_read(request):
    user = get_logged_in_user(request)
    if user:
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

def render_with_notifs(request, template_name, context):
    user = get_logged_in_user(request)
    notifs, unread_count = get_user_notifications(user)
    context['logged_in_user'] = user
    context['user'] = user
    context['user_role'] = request.session.get('role', user.role if user else None)
    context['user_notifications'] = notifs
    context['unread_notifications_count'] = unread_count
    return render(request, template_name, context)

def gamer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_logged_in_user(request)
        if not user:
            messages.warning(request, 'Please sign in to access your Gamer Dashboard.')
            return redirect('login')
        if user.role == 'pending':
            return redirect('complete_profile')
        if user.role == 'provider':
            messages.info(request, 'Redirected to your Provider Panel.')
            return redirect('provider_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def provider_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_logged_in_user(request)
        if not user:
            messages.warning(request, 'Please sign in to access the Provider Panel.')
            return redirect('login')
        if user.role == 'pending':
            return redirect('complete_profile')
        if user.role != 'provider':
            messages.info(request, 'Redirected to your Gamer Dashboard.')
            return redirect('gamer_dashboard')

        # Auto-initialize provider profile if user accesses provider features
        try:
            profile = user.provider_profile
        except ProviderProfile.DoesNotExist:
            profile = None

        if not profile:
            default_city = City.objects.first()
            ProviderProfile.objects.get_or_create(
                user=user,
                defaults={
                    'businessName': f"{user.firstName}'s Gaming Center",
                    'phone': 9313858614,
                    'address': 'CG Road, Navrangpura',
                    'city': default_city,
                    'is_verified': True
                }
            )
            if user.role != 'provider':
                user.role = 'provider'
                user.save(update_fields=['role'])
                request.session['role'] = 'provider'

        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_logged_in_user(request)
        if not user:
            messages.warning(request, 'Please sign in to access the Superadmin Platform Portal.')
            return redirect('login')
        # Allow superadmin, specified emails, or users with role='admin' or 'provider'
        admin_emails = ['admin@sparkzone.in', 'parshvabsukhadiya@gmail.com', 'sukhadiyavishvam22@gmail.com']
        if user.email in admin_emails or getattr(user, 'role', '') in ['admin', 'provider']:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access restricted to Platform Administrators.')
        return redirect('index')
    return wrapper

# ─── Uptime Health Check ───────────────────────────────────────────────────────
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy", "database": "connected", "platform": "SparkZone"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "database": str(e)}, status=500)

# ─── Landing & Marketplace Discovery ──────────────────────────────────────────
def index(request):
    categories = Category.objects.all()
    featured_games = Game.objects.filter(status='active').select_related('category', 'city', 'provider').prefetch_related('images', 'slots').order_by('-featured', '-timestamp')[:6]
    total_venues = ProviderProfile.objects.filter(is_verified=True).count() or 12
    total_systems = Game.objects.filter(status='active').aggregate(s=Sum('totalSystem'))['s'] or 84
    recent_reviews = Reviews.objects.select_related('user', 'game').order_by('-timestamp')[:6]

    return render_with_notifs(request, 'index.html', {
        'categories': categories,
        'games': featured_games,
        'total_venues': total_venues,
        'total_systems': total_systems,
        'reviews': recent_reviews,
    })

def games(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    city_id = request.GET.get('city')
    gpu_filter = request.GET.get('gpu')
    max_price = request.GET.get('max_price')
    min_rating = request.GET.get('min_rating')
    sort_by = request.GET.get('sort', 'featured')

    all_games = Game.objects.filter(status='active').select_related('category', 'city', 'provider').prefetch_related('images', 'slots', 'reviews').all()

    if q:
        all_games = all_games.filter(
            Q(name__icontains=q) |
            Q(available_games__icontains=q) |
            Q(description__icontains=q) |
            Q(gpu__icontains=q) |
            Q(address__icontains=q) |
            Q(provider__businessName__icontains=q)
        )
    if category_id:
        all_games = all_games.filter(category_id=category_id)
    if city_id:
        all_games = all_games.filter(city_id=city_id)
    if gpu_filter:
        if gpu_filter == '4090':
            all_games = all_games.filter(gpu__icontains='4090')
        elif gpu_filter == '4080':
            all_games = all_games.filter(gpu__icontains='4080')
        elif gpu_filter == 'ps5':
            all_games = all_games.filter(Q(category__categoryName__icontains='console') | Q(name__icontains='ps5') | Q(description__icontains='ps5'))
        elif gpu_filter == 'sim':
            all_games = all_games.filter(Q(category__categoryName__icontains='racing') | Q(name__icontains='sim') | Q(description__icontains='cockpit'))
    if max_price and max_price.isdigit():
        all_games = all_games.filter(pricePerHour__lte=float(max_price))

    cities = City.objects.all()
    categories = Category.objects.all()

    # Sorting
    if sort_by == 'price_low':
        all_games = all_games.order_by('pricePerHour')
    elif sort_by == 'price_high':
        all_games = all_games.order_by('-pricePerHour')
    else:
        all_games = all_games.order_by('-featured', '-timestamp')

    user = get_logged_in_user(request)
    favorite_ids = set(FavoriteVenue.objects.filter(user=user).values_list('game_id', flat=True)) if user else set()

    return render_with_notifs(request, 'games.html', {
        'games': all_games,
        'categories': categories,
        'cities': cities,
        'favorite_ids': favorite_ids,
        'selected_q': q,
        'selected_cat': category_id,
        'selected_city': city_id,
        'selected_gpu': gpu_filter,
        'selected_price': max_price,
        'selected_sort': sort_by,
    })

def categories(request):
    all_cats = Category.objects.annotate(station_count=Count('games')).all()
    return render_with_notifs(request, 'categories.html', {
        'categories': all_cats,
    })

def game_detail(request, game_id):
    game = get_object_or_404(
        Game.objects.select_related('category', 'city', 'provider').prefetch_related('images', 'slots', 'reviews__user'),
        id=game_id
    )
    user = get_logged_in_user(request)
    is_favorited = FavoriteVenue.objects.filter(user=user, game=game).exists() if user else False

    now = timezone.localtime(timezone.now())
    today = now.date()
    available_slots = game.slots.exclude(status='cancelled').filter(slotDate__gte=today).order_by('slotDate', 'startTime')

    reviews = game.reviews.select_related('user').order_by('-timestamp')
    avg_rating = game.get_avg_rating()
    review_count = game.get_review_count()

    return render_with_notifs(request, 'game_detail.html', {
        'game': game,
        'slots': available_slots,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'is_favorited': is_favorited,
        'razorpay_key_id': os.getenv('RAZORPAY_KEY_ID', 'rzp_test_sparkzone_mock')
    })

# ─── Instant Booking & Checkout (Razorpay + Pay at Venue) ─────────────────────
def gamer_checkout(request, game_id):
    game = get_object_or_404(Game.objects.select_related('category', 'city', 'provider'), id=game_id)
    user = get_logged_in_user(request)
    if not user:
        messages.warning(request, 'Please log in to lock your gaming station.')
        return redirect(f"/login/?next=/stations/{game_id}/")

    now = timezone.localtime(timezone.now())
    today_str = now.strftime('%Y-%m-%d')

    if request.method == 'POST':
        bookingDate = request.POST.get('bookingDate') or today_str
        startTime_str = request.POST.get('startTime') or now.strftime('%H:00')
        endTime_str = request.POST.get('endTime') or (now + timedelta(hours=1)).strftime('%H:00')
        slot_id = request.POST.get('slot_id')
        payment_method = request.POST.get('payment_method') or request.POST.get('paymentMethod') or 'razorpay'
        unit_numbers_raw = request.POST.get('unit_numbers') or request.POST.get('unit_number', '')

        selected_units = []
        for item in str(unit_numbers_raw).split(','):
            item = item.strip()
            if item.isdigit():
                u_val = int(item)
                if u_val not in selected_units:
                    selected_units.append(u_val)

        if not selected_units:
            selected_units = [1]

        fmt = '%H:%M'
        try:
            start_t = datetime.strptime(startTime_str, fmt).time()
            end_t = datetime.strptime(endTime_str, fmt).time()
            hours = (datetime.combine(now.date(), end_t) - datetime.combine(now.date(), start_t)).seconds / 3600
            if hours <= 0:
                hours = 1.0
        except Exception:
            start_t = time(now.hour, 0)
            end_t = time(min(now.hour + 1, 23), 0)
            hours = 1.0

        with db_transaction.atomic():
            slot_obj = None
            if slot_id:
                slot_obj = Slot.objects.select_for_update().filter(id=slot_id, game=game).first()
                if slot_obj and slot_obj.is_full(start_time=start_t, end_time=end_t):
                    messages.error(request, 'That slot capacity was just filled! Please choose another slot.')
                    return redirect('game_detail', game_id=game_id)

            # Prevent unit collision
            active_conflicts = Booking.objects.filter(
                game=game,
                bookingDate=bookingDate,
                status__in=['confirmed', 'completed'],
                startTime__lt=end_t,
                endTime__gt=start_t
            )
            already_booked = set()
            for b in active_conflicts:
                for u in b.get_unit_numbers_list():
                    already_booked.add(u)

            for u in selected_units:
                if u in already_booked:
                    messages.error(request, f"Unit {u} was just booked by another gamer! Please select an open unit.")
                    return redirect('game_detail', game_id=game_id)

            rate = slot_obj.get_price() if slot_obj else game.pricePerHour
            total_amount = round(float(hours * rate * len(selected_units)), 2)
            unit_numbers_str = ", ".join(str(x) for x in selected_units)

            # INSTANT LOCK BOOKING!
            booking_obj = Booking.objects.create(
                user=user,
                game=game,
                slot=slot_obj,
                bookingDate=bookingDate,
                startTime=start_t,
                endTime=end_t,
                totalAmount=total_amount,
                status='confirmed',
                payment_status='paid_online' if payment_method == 'razorpay' else 'pay_at_venue',
                unit_number=selected_units[0],
                unit_numbers=unit_numbers_str
            )

            # Generate Razorpay order if online prepayment
            razorpay_order_id = None
            if payment_method == 'razorpay':
                order_res = create_razorpay_order(total_amount, receipt_id=booking_obj.id, notes={'booking_id': str(booking_obj.id)})
                if order_res.get('success'):
                    razorpay_order_id = order_res.get('order_id')

            Payment.objects.create(
                user=user,
                booking=booking_obj,
                amount=total_amount,
                paymentMethod=payment_method,
                paymentStatus='completed' if payment_method == 'razorpay' else 'pending',
                razorpay_order_id=razorpay_order_id
            )

            # Update Slot capacity
            if slot_obj:
                slot_obj.bookedCount = slot_obj.bookedCount + len(selected_units)
                if slot_obj.bookedCount >= slot_obj.capacity:
                    slot_obj.status = 'booked'
                slot_obj.save()

            # Broadcast live WebSockets update to all other connected clients
            broadcast_station_update(game.id, 'unit_locked', {
                'locked_units': selected_units,
                'booking_date': str(bookingDate),
                'booking_id': booking_obj.id
            })

            # In-app notification to provider
            if game.provider and hasattr(game.provider, 'user'):
                Notification.objects.create(
                    user=game.provider.user,
                    booking=booking_obj,
                    title="⚡ Instant Station Booking Confirmed!",
                    message=f"{user.firstName} locked Unit(s) {unit_numbers_str} at {game.name} on {bookingDate} ({startTime_str}-{endTime_str}) - ₹{total_amount:.0f} ({booking_obj.get_payment_status_display()})."
                )

            # Trigger SMTP Email & MSG91 SMS confirmations
            send_booking_confirmation_email(user, booking_obj)
            user_prof = UserProfile.objects.filter(user=user).first()
            phone = getattr(user_prof, 'phone', None)
            if phone:
                send_booking_confirmation_sms(phone, booking_obj)

        if payment_method == 'razorpay' and (request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')):
            return JsonResponse({
                'status': 'razorpay_checkout',
                'razorpay_key': os.getenv('RAZORPAY_KEY_ID', 'rzp_test_mock_sparkzone'),
                'razorpay_order_id': razorpay_order_id,
                'amount': total_amount,
                'booking_id': booking_obj.id,
                'game_name': game.name,
                'unit_number': booking_obj.unit_number,
            })

        messages.success(request, f"✓ Pass Confirmed! Unit(s) {unit_numbers_str} are reserved for you.")
        return redirect('gamer_dashboard')

    available_slots = game.slots.exclude(status='cancelled').filter(slotDate__gte=now.date()).order_by('slotDate', 'startTime')
    return render_with_notifs(request, 'booking.html', {
        'game': game,
        'available_slots': available_slots,
        'today': today_str,
    })

def razorpay_verify(request):
    """
    Handles Razorpay Checkout callback for signature validation.
    """
    if request.method == 'POST':
        order_id = request.POST.get('razorpay_order_id')
        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')
        booking_id = request.POST.get('booking_id')

        if verify_razorpay_signature(order_id, payment_id, signature):
            booking = get_object_or_404(Booking, id=booking_id)
            booking.payment_status = 'paid_online'
            booking.save()
            payment = Payment.objects.filter(booking=booking).first()
            if payment:
                payment.paymentStatus = 'completed'
                payment.razorpay_order_id = order_id
                payment.razorpay_payment_id = payment_id
                payment.razorpay_signature = signature
                payment.save()
            return JsonResponse({'status': 'success', 'message': 'Payment verified successfully'})
        return JsonResponse({'status': 'failed', 'error': 'Signature verification failed'}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def cancel_booking(request, booking_id):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    with db_transaction.atomic():
        booking = get_object_or_404(Booking.objects.select_related('game', 'user', 'game__provider'), id=booking_id)
        is_owner = (booking.user_id == user.id)
        is_provider = (booking.game.provider and booking.game.provider.user_id == user.id)

        if not (is_owner or is_provider):
            messages.error(request, 'Unauthorized action.')
            return redirect('index')

        if booking.status in ['cancelled', 'completed', 'no_show']:
            messages.info(request, f"Booking is already {booking.get_status_display()}.")
            return redirect('gamer_dashboard' if is_owner else 'provider_bookings')

        refund_amount = 0
        payment = Payment.objects.filter(booking=booking).first()
        if payment and payment.paymentStatus == 'completed' and payment.razorpay_payment_id:
            refund_res = process_razorpay_refund(payment.razorpay_payment_id, amount_in_rupees=booking.totalAmount)
            if refund_res.get('success'):
                booking.refund_id = refund_res.get('refund_id')
                payment.refund_id = refund_res.get('refund_id')
                payment.paymentStatus = 'refunded'
                payment.save()
                refund_amount = booking.totalAmount

        booking.status = 'cancelled'
        booking.payment_status = 'refunded' if refund_amount > 0 else 'cancelled'
        booking.save()

        # Free slot capacity
        if booking.slot_id:
            slot = Slot.objects.select_for_update().filter(id=booking.slot_id).first()
            if slot:
                num_u = len(booking.get_unit_numbers_list()) or 1
                slot.bookedCount = max(0, slot.bookedCount - num_u)
                if slot.status == 'booked' and slot.bookedCount < slot.capacity:
                    slot.status = 'available'
                slot.save()

        # Broadcast live sync
        broadcast_station_update(booking.game_id, 'booking_cancelled', {
            'freed_units': booking.get_unit_numbers_list(),
            'booking_id': booking.id
        })

        # Notifications & Receipts
        send_cancellation_email(booking.user, booking, refund_amount=refund_amount)
        user_prof = UserProfile.objects.filter(user=booking.user).first()
        if user_prof and user_prof.phone:
            send_cancellation_sms(user_prof.phone, booking, refund_amount=refund_amount)

    refund_msg = f" Refund of ₹{refund_amount:.0f} initiated via Razorpay." if refund_amount > 0 else ""
    messages.success(request, f"Booking #{booking.id} cancelled successfully.{refund_msg}")
    return redirect('gamer_dashboard' if is_owner else 'provider_bookings')

@gamer_required
def submit_review(request, booking_id):
    user = get_logged_in_user(request)
    booking = get_object_or_404(Booking, id=booking_id, user=user)

    if request.method == 'POST':
        try:
            rating = float(request.POST.get('rating', 5.0))
        except ValueError:
            rating = 5.0
        comment = request.POST.get('comment', '').strip()

        Reviews.objects.update_or_create(
            booking=booking,
            defaults={
                'user': user,
                'game': booking.game,
                'rating': min(5.0, max(1.0, rating)),
                'comment': comment,
                'is_verified_booking': True
            }
        )
        messages.success(request, '⭐ Thank you! Your verified review has been published.')
    return redirect('gamer_dashboard')

def api_toggle_favorite(request, game_id):
    user = get_logged_in_user(request)
    if not user:
        return JsonResponse({'error': 'Please sign in'}, status=401)
    game = get_object_or_404(Game, id=game_id)
    fav = FavoriteVenue.objects.filter(user=user, game=game).first()
    if fav:
        fav.delete()
        return JsonResponse({'favorited': False})
    else:
        FavoriteVenue.objects.create(user=user, game=game)
        return JsonResponse({'favorited': True})

# ─── Gamer Dashboard & Profile ────────────────────────────────────────────────
@gamer_required
def gamer_dashboard(request):
    user = get_logged_in_user(request)
    all_bookings = list(Booking.objects.filter(user=user).select_related('game', 'game__category', 'game__city').order_by('-timestamp'))
    payments = {p.booking_id: p for p in Payment.objects.filter(booking__in=all_bookings)}
    for b in all_bookings:
        b.payment_info = payments.get(b.id)

    active_passes = [b for b in all_bookings if b.status in ['confirmed', 'pending']]
    completed_sessions = [b for b in all_bookings if b.status == 'completed']
    cancelled_passes = [b for b in all_bookings if b.status in ['cancelled', 'no_show']]
    total_spent = sum(b.totalAmount for b in all_bookings if b.status in ['confirmed', 'completed'])

    favorite_venues = FavoriteVenue.objects.filter(user=user).select_related('game', 'game__category', 'game__city')

    return render_with_notifs(request, 'gamer/dashboard.html', {
        'all_bookings': all_bookings,
        'active_passes': active_passes,
        'completed_sessions': completed_sessions,
        'cancelled_passes': cancelled_passes,
        'total_bookings': len(all_bookings),
        'total_spent': total_spent,
        'favorite_venues': favorite_venues,
        'active_tab': request.GET.get('tab', 'passes'),
    })

def my_bookings(request):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')
    if user.role == 'provider':
        return redirect('provider_dashboard')
    return redirect('gamer_dashboard')

# ─── Provider Operations Panel ────────────────────────────────────────────────
@provider_required
def provider_dashboard(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile

    if not Game.objects.filter(provider=provider).exists():
        Game.objects.filter(provider__isnull=True).update(provider=provider)

    games = Game.objects.filter(provider=provider).select_related('category', 'city').prefetch_related('slots').order_by('-timestamp')

    now = timezone.localtime(timezone.now())
    today = now.date()

    all_bookings = Booking.objects.filter(game__provider=provider).select_related('user', 'game', 'slot').order_by('-timestamp')
    today_bookings = all_bookings.filter(bookingDate=today)
    active_now = today_bookings.filter(status='confirmed')

    total_earnings = sum(p.amount for p in Payment.objects.filter(booking__game__provider=provider, paymentStatus='completed'))
    today_earnings = sum(p.amount for p in Payment.objects.filter(booking__in=today_bookings, paymentStatus='completed'))
    today_venue_pay = sum(b.totalAmount for b in today_bookings.filter(payment_status='pay_at_venue'))

    total_units_count = sum(g.totalSystem for g in games)
    total_slots_count = Slot.objects.filter(game__provider=provider).count()

    # Occupancy rate calculation
    occupied_units_count = sum(len(b.get_unit_numbers_list()) for b in active_now)
    occupancy_pct = min(100, int((occupied_units_count / max(1, total_units_count)) * 100))

    return render_with_notifs(request, 'provider/dashboard.html', {
        'provider': provider,
        'games': games,
        'today_bookings': today_bookings[:12],
        'active_now_bookings': active_now,
        'total_earnings': total_earnings,
        'today_earnings': today_earnings,
        'today_venue_pay': today_venue_pay,
        'total_units_count': total_units_count,
        'total_slots_count': total_slots_count,
        'total_bookings_count': all_bookings.count(),
        'occupancy_pct': occupancy_pct,
    })

@provider_required
def provider_stations(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    games = Game.objects.filter(provider=provider).select_related('category', 'city').prefetch_related('slots').order_by('-timestamp')
    return render_with_notifs(request, 'provider/stations.html', {
        'provider': provider,
        'games': games,
    })

@provider_required
def provider_game_add(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    categories = Category.objects.all()
    cities = City.objects.select_related('state').all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        city_id = request.POST.get('city')
        available_games = request.POST.get('available_games', '').strip()
        description = request.POST.get('description', '').strip()
        address = request.POST.get('address', '').strip()
        price_val = request.POST.get('pricePerHour')
        pricePerHour = float(price_val) if price_val and price_val.strip() else 200.0
        totalSystem = int(request.POST.get('totalSystem', 1))
        gpu = request.POST.get('gpu', '').strip()
        cpu = request.POST.get('cpu', '').strip()
        ram = request.POST.get('ram', '').strip()
        display_specs = request.POST.get('display_specs', '').strip()
        peripherals = request.POST.get('peripherals', '').strip()
        operating_hours = request.POST.get('operating_hours', '09:00 AM - 11:00 PM').strip()
        status = request.POST.get('status', 'active')
        image_url = request.POST.get('image_url', '').strip()
        image_file = request.FILES.get('image')

        cat_obj = get_object_or_404(Category, id=category_id)
        city_obj = get_object_or_404(City, id=city_id)

        new_game = Game.objects.create(
            provider=provider,
            category=cat_obj,
            city=city_obj,
            name=name,
            available_games=available_games,
            description=description,
            address=address,
            pricePerHour=pricePerHour,
            totalSystem=totalSystem,
            availableSystems=totalSystem,
            gpu=gpu or None,
            cpu=cpu or None,
            ram=ram or None,
            display_specs=display_specs or None,
            peripherals=peripherals or None,
            image_url=image_url if image_url else None,
            image=image_file if image_file else None,
            operating_hours=operating_hours or '09:00 AM - 11:00 PM',
            status=status
        )

        gallery_files = request.FILES.getlist('gallery_images')
        for gf in gallery_files:
            GameImages.objects.create(game=new_game, image=gf)

        broadcast_station_update(new_game.id, 'station_created')
        messages.success(request, f'Gaming Station "{name}" added successfully!')
        return redirect('provider_stations')

    return render_with_notifs(request, 'provider/game_form.html', {
        'is_edit': False,
        'categories': categories,
        'cities': cities,
    })

@provider_required
def provider_game_edit(request, game_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    game = get_object_or_404(Game, id=game_id, provider=provider)
    categories = Category.objects.all()
    cities = City.objects.select_related('state').all()

    if request.method == 'POST':
        game.name = request.POST.get('name', '').strip()
        game.category_id = request.POST.get('category')
        game.city_id = request.POST.get('city')
        game.available_games = request.POST.get('available_games', '').strip()
        game.description = request.POST.get('description', '').strip()
        game.address = request.POST.get('address', '').strip()
        price_val = request.POST.get('pricePerHour')
        if price_val and price_val.strip():
            game.pricePerHour = float(price_val)
        game.totalSystem = int(request.POST.get('totalSystem', 1))
        game.gpu = request.POST.get('gpu', '').strip() or None
        game.cpu = request.POST.get('cpu', '').strip() or None
        game.ram = request.POST.get('ram', '').strip() or None
        game.display_specs = request.POST.get('display_specs', '').strip() or None
        game.peripherals = request.POST.get('peripherals', '').strip() or None
        game.operating_hours = request.POST.get('operating_hours', '09:00 AM - 11:00 PM').strip()
        game.status = request.POST.get('status', 'active')

        image_file = request.FILES.get('image')
        if image_file:
            game.image = image_file
        elif request.POST.get('image_url'):
            game.image_url = request.POST.get('image_url').strip()

        game.save()

        gallery_files = request.FILES.getlist('gallery_images')
        for gf in gallery_files:
            GameImages.objects.create(game=game, image=gf)

        broadcast_station_update(game.id, 'station_updated')
        messages.success(request, f'Station "{game.name}" updated successfully!')
        return redirect('provider_stations')

    return render_with_notifs(request, 'provider/game_form.html', {
        'is_edit': True,
        'game': game,
        'categories': categories,
        'cities': cities,
    })

@provider_required
def provider_game_delete(request, game_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    game = get_object_or_404(Game, id=game_id, provider=provider)

    if Booking.objects.filter(game=game).exists():
        game.status = 'inactive'
        game.save()
        messages.info(request, f'Station "{game.name}" deactivated to protect past booking records.')
    else:
        game.delete()
        messages.success(request, 'Station deleted successfully.')

    return redirect('provider_stations')

@provider_required
def provider_slot_manage(request, game_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    game = get_object_or_404(Game, id=game_id, provider=provider)

    if request.method == 'POST':
        slotDate = request.POST.get('slotDate')
        startTime = request.POST.get('startTime')
        endTime = request.POST.get('endTime')
        capacity = int(request.POST.get('capacity', game.totalSystem))
        price_val = request.POST.get('price', '').strip()
        price = float(price_val) if price_val else None

        Slot.objects.create(
            game=game,
            slotDate=slotDate,
            startTime=startTime,
            endTime=endTime,
            capacity=capacity,
            price=price,
            status='available'
        )
        broadcast_station_update(game.id, 'slot_created')
        messages.success(request, 'New time slot created successfully!')
        return redirect('provider_slot_manage', game_id=game_id)

    selected_date = request.GET.get('date')
    slots = Slot.objects.filter(game=game).order_by('slotDate', 'startTime')
    if selected_date:
        slots = slots.filter(slotDate=selected_date)

    return render_with_notifs(request, 'provider/slots.html', {
        'game': game,
        'slots': slots,
        'selected_date': selected_date,
    })

@provider_required
def provider_slot_bulk_generate(request, game_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    game = get_object_or_404(Game, id=game_id, provider=provider)

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date') or start_date_str
        start_hour = int(request.POST.get('start_hour', 10))
        end_hour = int(request.POST.get('end_hour', 23))
        slot_duration = int(request.POST.get('duration_hours', 1))
        price_val = request.POST.get('price')
        price = float(price_val) if price_val else game.pricePerHour

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except Exception:
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=6)

        current_date = start_date
        created_count = 0

        while current_date <= end_date:
            for h in range(start_hour, end_hour, slot_duration):
                slot_start = time(h, 0)
                end_h = min(h + slot_duration, 23)
                slot_end = time(end_h, 59 if end_h == 23 else 0)

                if not Slot.objects.filter(game=game, slotDate=current_date, startTime=slot_start).exists():
                    Slot.objects.create(
                        game=game,
                        slotDate=current_date,
                        startTime=slot_start,
                        endTime=slot_end,
                        capacity=game.totalSystem,
                        price=price,
                        status='available'
                    )
                    created_count += 1
            current_date += timedelta(days=1)

        broadcast_station_update(game.id, 'bulk_slots_generated', {'count': created_count})
        messages.success(request, f'⚡ Generated {created_count} time slots across {game.name}!')
    return redirect('provider_slot_manage', game_id=game_id)

@provider_required
def provider_slot_delete(request, slot_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    slot = get_object_or_404(Slot, id=slot_id, game__provider=provider)
    game_id = slot.game_id

    if Booking.objects.filter(slot=slot).exists():
        slot.status = 'cancelled'
        slot.save()
        messages.warning(request, 'Slot blocked/cancelled to preserve past bookings.')
    else:
        slot.delete()
        messages.success(request, 'Time slot deleted.')

    broadcast_station_update(game_id, 'slot_deleted')
    return redirect('provider_slot_manage', game_id=game_id)

@provider_required
def provider_bookings(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile

    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    station_id = request.GET.get('station')
    search_q = request.GET.get('q', '').strip()

    bookings = Booking.objects.filter(game__provider=provider).select_related('user', 'game', 'slot').order_by('-timestamp')

    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(bookingDate=date_filter)
    if station_id:
        bookings = bookings.filter(game_id=station_id)
    if search_q:
        bookings = bookings.filter(
            Q(user__firstName__icontains=search_q) |
            Q(user__lastName__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(unit_numbers__icontains=search_q) |
            Q(id__icontains=search_q)
        )

    games = Game.objects.filter(provider=provider)
    return render_with_notifs(request, 'provider/bookings.html', {
        'provider': provider,
        'bookings': bookings,
        'games': games,
        'selected_status': status_filter,
        'selected_date': date_filter,
        'selected_station': station_id,
        'search_q': search_q,
    })

@provider_required
def provider_booking_checkin(request, booking_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    booking = get_object_or_404(Booking, id=booking_id, game__provider=provider)

    booking.status = 'completed'
    booking.check_in_time = timezone.now()
    if booking.payment_status == 'pay_at_venue':
        booking.payment_status = 'paid_online'
        p = Payment.objects.filter(booking=booking).first()
        if p:
            p.paymentStatus = 'completed'
            p.save()
    booking.save()

    broadcast_station_update(booking.game_id, 'gamer_checked_in', {'booking_id': booking.id})
    messages.success(request, f"✓ Gamer {booking.user.firstName} checked in! Session marked completed.")
    return redirect('provider_bookings')

@provider_required
def provider_booking_noshow(request, booking_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    booking = get_object_or_404(Booking, id=booking_id, game__provider=provider)

    booking.status = 'no_show'
    booking.save()

    # Release slot capacity
    if booking.slot_id:
        slot = Slot.objects.filter(id=booking.slot_id).first()
        if slot:
            num_u = len(booking.get_unit_numbers_list()) or 1
            slot.bookedCount = max(0, slot.bookedCount - num_u)
            if slot.status == 'booked':
                slot.status = 'available'
            slot.save()

    broadcast_station_update(booking.game_id, 'booking_noshow', {'booking_id': booking.id})
    messages.warning(request, f"Booking #{booking.id} marked as No-Show. Units released.")
    return redirect('provider_bookings')

# ─── Superadmin Platform Oversight Portal ─────────────────────────────────────
@admin_required
def superadmin_dashboard(request):
    total_venues = ProviderProfile.objects.count()
    verified_venues = ProviderProfile.objects.filter(is_verified=True).count()
    total_gamers = User.objects.filter(role='user').count()
    total_bookings = Booking.objects.count()
    total_gmv = sum(p.amount for p in Payment.objects.filter(paymentStatus='completed'))
    platform_revenue = total_gmv * 0.10  # 10% platform take rate

    all_providers = ProviderProfile.objects.select_related('user', 'city').all().order_by('-timestamp')
    recent_bookings = Booking.objects.select_related('user', 'game', 'game__provider').order_by('-timestamp')[:20]

    return render_with_notifs(request, 'admin_platform/dashboard.html', {
        'total_venues': total_venues,
        'verified_venues': verified_venues,
        'total_gamers': total_gamers,
        'total_bookings': total_bookings,
        'total_gmv': total_gmv,
        'platform_revenue': platform_revenue,
        'providers': all_providers,
        'recent_bookings': recent_bookings,
    })

@admin_required
def superadmin_toggle_verify(request, provider_id):
    provider = get_object_or_404(ProviderProfile, id=provider_id)
    provider.is_verified = not provider.is_verified
    provider.save()
    status_str = "Verified" if provider.is_verified else "Unverified"
    messages.success(request, f"Venue '{provider.businessName}' status set to {status_str}.")
    return redirect('superadmin_dashboard')

# ─── Real-Time Unit Availability & Maintenance APIs ───────────────────────────
def get_unit_availability_api(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    date_str = request.GET.get('date')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')

    total_systems = game.totalSystem or 1
    disabled_units = game.get_disabled_units_set()
    units = []

    now = timezone.localtime(timezone.now())
    if not date_str:
        date_str = now.strftime('%Y-%m-%d')
    if not start_time_str:
        start_time_str = now.strftime('%H:00')
    if not end_time_str:
        end_time_str = (now + timedelta(hours=1)).strftime('%H:00')

    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        fmt = '%H:%M'
        start_time = datetime.strptime(start_time_str, fmt).time()
        end_time = datetime.strptime(end_time_str, fmt).time()

        active_bookings = Booking.objects.filter(
            game=game,
            bookingDate=booking_date,
            status__in=['confirmed', 'completed', 'pending'],
            startTime__lt=end_time,
            endTime__gt=start_time
        ).select_related('user')

        booked_units_map = {}
        for b in active_bookings:
            b_units = b.get_unit_numbers_list()
            info = {
                'booking_id': b.id,
                'user_name': f"{b.user.firstName} {b.user.lastName}",
                'user_email': b.user.email,
                'time_slot': f"{b.startTime.strftime('%H:%M')} - {b.endTime.strftime('%H:%M')}",
                'status_display': b.get_status_display()
            }
            for bu in b_units:
                booked_units_map[bu] = info

        for u in range(1, total_systems + 1):
            if u in disabled_units:
                st = 'maintenance'
                details = None
            elif u in booked_units_map:
                st = 'booked'
                details = booked_units_map[u]
            else:
                st = 'available'
                details = None

            units.append({
                'unit_number': u,
                'status': st,
                'details': details
            })
    except Exception:
        for u in range(1, total_systems + 1):
            st = 'maintenance' if u in disabled_units else 'available'
            units.append({'unit_number': u, 'status': st, 'details': None})

    return JsonResponse({
        'total_systems': total_systems,
        'disabled_units': list(disabled_units),
        'units': units,
        'date': date_str,
        'start_time': start_time_str,
        'end_time': end_time_str
    })

def provider_toggle_unit_maintenance_api(request, game_id):
    user = get_logged_in_user(request)
    if not user or user.role != 'provider':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    game = get_object_or_404(Game, id=game_id, provider=user.provider_profile)
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        unit_num = data.get('unit_number') or request.POST.get('unit_number')
        if unit_num:
            try:
                u_int = int(unit_num)
                disabled_set = game.get_disabled_units_set()
                if u_int in disabled_set:
                    disabled_set.remove(u_int)
                else:
                    disabled_set.add(u_int)

                game.out_of_service_units = ", ".join(str(x) for x in sorted(disabled_set))
                game.save()
                broadcast_station_update(game.id, 'maintenance_toggled', {'disabled_units': list(disabled_set)})
                return JsonResponse({'success': True, 'disabled_units': list(disabled_set)})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

# ─── User Authentication & Registration ────────────────────────────────────────
def get_google_redirect_uri(request):
    explicit_uri = os.getenv('GOOGLE_REDIRECT_URI')
    if explicit_uri:
        return explicit_uri.strip()

    redirect_uri = request.build_absolute_uri('/google-login/').split('?')[0]
    if request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https' or 'vercel' in request.get_host() or request.META.get('HTTP_X_FORWARDED_SSL') == 'on':
        redirect_uri = redirect_uri.replace('http://', 'https://')
    return redirect_uri

def _authenticate_google_user(request, email, first_name='', last_name=''):
    email = email.lower().strip()
    if not first_name:
        first_name = email.split('@')[0].capitalize()
    if not last_name:
        last_name = 'User'

    existing_user = User.objects.filter(email=email).first()
    if not existing_user:
        temp_password = hashlib.sha256(f"GoogleOAuth_{email}_sparkzone_secure".encode()).hexdigest()
        user = User.objects.create(
            email=email,
            firstName=first_name,
            lastName=last_name,
            password=temp_password,
            role='pending'
        )
        request.session['user_id'] = user.id
        request.session['role'] = 'pending'
        request.session['pending_role_selection'] = True
        messages.info(request, f'Welcome to SparkZone, {first_name}! Please choose your role to complete your profile.')
        return redirect('complete_profile')
    else:
        user = existing_user
        request.session['user_id'] = user.id
        request.session['role'] = user.role
        request.session.pop('pending_role_selection', None)

        if user.role == 'pending':
            return redirect('complete_profile')

        messages.success(request, f'Welcome back, {user.firstName}!')
        if user.role == 'provider':
            return redirect('provider_dashboard')
        return redirect('gamer_dashboard')

def google_login(request):
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    email_param = request.POST.get('email') or request.GET.get('email')
    if email_param:
        email = email_param.strip().lower()
        if '@' in email and '.' in email:
            name = request.POST.get('name') or request.GET.get('name') or ''
            name_parts = name.strip().split(' ', 1) if name else []
            first_name = name_parts[0] if name_parts else email.split('@')[0].capitalize()
            last_name = name_parts[1] if len(name_parts) > 1 else 'User'
            return _authenticate_google_user(request, email, first_name, last_name)
        else:
            messages.error(request, 'Please enter a valid Google email address.')
            return render_with_notifs(request, 'google_login_prompt.html', {
                'oauth_configured': bool(client_id and client_secret)
            })

    if request.GET.get('error'):
        error_desc = request.GET.get('error_description') or request.GET.get('error')
        messages.warning(request, f"Google OAuth notice: {error_desc}. You can sign in using an account below.")
        return render_with_notifs(request, 'google_login_prompt.html', {
            'oauth_configured': bool(client_id and client_secret)
        })

    code = request.GET.get('code')
    redirect_uri = get_google_redirect_uri(request)

    if client_id and client_secret and not request.GET.get('prompt'):
        if not code:
            import urllib.parse
            params = urllib.parse.urlencode({
                'client_id': client_id,
                'response_type': 'code',
                'scope': 'openid email profile',
                'redirect_uri': redirect_uri,
                'prompt': 'select_account'
            })
            return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")

        try:
            import urllib.parse
            import urllib.request
            token_url = "https://oauth2.googleapis.com/token"
            token_data = urllib.parse.urlencode({
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }).encode('utf-8')

            req = urllib.request.Request(token_url, data=token_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req) as resp:
                token_json = json.loads(resp.read().decode('utf-8'))
                access_token = token_json.get('access_token')

            if not access_token:
                messages.error(request, 'Failed to obtain access token from Google.')
                return render_with_notifs(request, 'google_login_prompt.html', {'oauth_configured': True})

            user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
            req_info = urllib.request.Request(user_info_url)
            with urllib.request.urlopen(req_info) as resp:
                info = json.loads(resp.read().decode('utf-8'))

            email = info.get('email')
            if not email:
                messages.error(request, 'Google account did not return a valid email address.')
                return render_with_notifs(request, 'google_login_prompt.html', {'oauth_configured': True})

            first_name = info.get('given_name') or info.get('name', 'Google').split()[0]
            last_name = info.get('family_name') or 'User'

            return _authenticate_google_user(request, email, first_name, last_name)
        except Exception as e:
            messages.warning(request, f"Google OAuth issue: {str(e)}. You can choose an account below.")
            return render_with_notifs(request, 'google_login_prompt.html', {'oauth_configured': True})

    return render_with_notifs(request, 'google_login_prompt.html', {
        'oauth_configured': bool(client_id and client_secret)
    })

def register(request):
    cities = City.objects.select_related('state').all()
    if request.method == 'POST':
        firstName = request.POST.get('firstName', '').strip()
        lastName = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        role = request.POST.get('role', 'user')
        phone_val = request.POST.get('phone', '').strip()

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            messages.error(request, 'Please enter a valid email address.')
            return render_with_notifs(request, 'register.html', {'cities': cities})

        if role == 'provider' or phone_val:
            if not re.match(r'^\d{10}$', phone_val):
                messages.error(request, 'Mobile phone number must be exactly 10 digits.')
                return render_with_notifs(request, 'register.html', {'cities': cities})

        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return render_with_notifs(request, 'register.html', {'cities': cities})

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render_with_notifs(request, 'register.html', {'cities': cities})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with that email already exists. Please log in.')
            return redirect('login')

        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User.objects.create(
            firstName=firstName,
            lastName=lastName,
            email=email,
            password=hashed,
            role=role,
        )

        phone_num = int(phone_val) if phone_val.isdigit() else 9313858614

        if role == 'provider':
            business_name = request.POST.get('businessName', '').strip() or f"{firstName}'s Gaming Lounge"
            city_id = request.POST.get('city')
            address = request.POST.get('address', '').strip() or 'Ahmedabad Arena'
            city = City.objects.filter(id=city_id).first() or cities.first()

            ProviderProfile.objects.create(
                user=user,
                businessName=business_name,
                phone=phone_num,
                address=address,
                city=city,
                is_verified=True
            )
        else:
            default_country = Country.objects.first()
            default_state = State.objects.first()
            default_city = cities.first()
            if default_city and default_country and default_state:
                UserProfile.objects.create(
                    user=user,
                    phone=phone_num,
                    address="Gamer Headquarters",
                    country=default_country,
                    state=default_state,
                    city=default_city
                )

        request.session['user_id'] = user.id
        request.session['role'] = user.role
        messages.success(request, f'Welcome to SparkZone, {firstName}! Your account has been created.')

        if user.role == 'provider':
            return redirect('provider_dashboard')
        return redirect('gamer_dashboard')

    return render_with_notifs(request, 'register.html', {'cities': cities})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        hashed = hashlib.sha256(password.encode()).hexdigest()

        user = User.objects.filter(email=email, password=hashed).first()
        if user:
            request.session['user_id'] = user.id
            request.session['role'] = user.role

            if user.role == 'pending':
                return redirect('complete_profile')

            messages.success(request, f'Welcome back, {user.firstName}!')
            next_url = request.GET.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)

            if user.role == 'provider':
                return redirect('provider_dashboard')
            return redirect('gamer_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render_with_notifs(request, 'login.html', {})

def complete_profile(request):
    user = get_logged_in_user(request)
    if not user:
        messages.warning(request, 'Please sign in to complete your profile.')
        return redirect('login')

    if user.role in ['user', 'provider']:
        request.session['role'] = user.role
        request.session.pop('pending_role_selection', None)
        if user.role == 'provider':
            return redirect('provider_dashboard')
        return redirect('gamer_dashboard')

    if request.method == 'POST':
        selected_role = request.POST.get('role', 'user').strip()
        if selected_role not in ['user', 'provider']:
            selected_role = 'user'

        user.role = selected_role
        user.save(update_fields=['role'])
        request.session['role'] = selected_role
        request.session.pop('pending_role_selection', None)

        if selected_role == 'provider':
            default_city = City.objects.first()
            ProviderProfile.objects.get_or_create(
                user=user,
                defaults={
                    'businessName': f"{user.firstName}'s Gaming Center",
                    'phone': 9313858614,
                    'address': 'CG Road, Navrangpura',
                    'city': default_city,
                    'is_verified': True
                }
            )
            messages.success(request, f'Profile completed! Welcome to your Provider Panel, {user.firstName}.')
            return redirect('provider_dashboard')
        else:
            messages.success(request, f'Profile completed! Welcome to your Gamer Dashboard, {user.firstName}.')
            return redirect('gamer_dashboard')

    return render_with_notifs(request, 'complete_profile.html', {'pending_user': user})

def logout_view(request):
    request.session.flush()
    messages.success(request, 'Signed out successfully.')
    return redirect('index')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            messages.error(request, 'Please enter a valid email address.')
            return render_with_notifs(request, 'contact.html', {})

        phone_num = int(phone) if phone.isdigit() and len(phone) == 10 else 9313858614
        ContactUs.objects.create(
            name=name,
            email=email,
            phone=phone_num,
            message=message,
        )
        messages.success(request, 'Message received! A gaming specialist will get back to you shortly.')
        return redirect('contact')

    return render_with_notifs(request, 'contact.html', {})
