from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection, transaction as db_transaction
from django.db.models import Q
from django.utils import timezone
from functools import wraps
from .models import *
import hashlib

# ─── Helper & Decorators ────────────────────────────────────────────────────────
def get_logged_in_user(request):
    uid = request.session.get('user_id')
    if uid:
        try:
            return User.objects.select_related('provider_profile').get(id=uid)
        except User.DoesNotExist:
            request.session.pop('user_id', None)
    return None

def get_user_notifications(user):
    if not user:
        return [], 0
    notifs = Notification.objects.filter(user=user).order_by('-timestamp')[:10]
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    return notifs, unread_count

def render_with_notifs(request, template_name, context):
    user = get_logged_in_user(request)
    notifs, unread_count = get_user_notifications(user)
    context['logged_in_user'] = user
    context['user_notifications'] = notifs
    context['unread_notifications_count'] = unread_count
    return render(request, template_name, context)

def provider_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_logged_in_user(request)
        if not user:
            messages.warning(request, 'Please log in to access the Provider Panel.')
            return redirect('login')

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

        return view_func(request, *args, **kwargs)
    return wrapper

# ─── Uptime Health Check Endpoint ──────────────────────────────────────────────
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy", "database": "connected"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "database": str(e)}, status=500)

# ─── Home ───────────────────────────────────────────────────────────────────────
def index(request):
    categories = Category.objects.all()
    games = Game.objects.filter(status='active').select_related('category', 'city', 'provider').prefetch_related('images', 'slots').all()[:6]
    reviews = Reviews.objects.select_related('user', 'game').order_by('-timestamp')[:6]
    return render_with_notifs(request, 'index.html', {
        'categories': categories,
        'games': games,
        'reviews': reviews,
    })

# ─── Games Listing ──────────────────────────────────────────────────────────────
def games(request):
    category_id = request.GET.get('category')
    search = request.GET.get('search', '')
    all_games = Game.objects.filter(status='active').select_related('category', 'city', 'provider').prefetch_related('images', 'slots').all()
    categories = Category.objects.all()

    if category_id:
        all_games = all_games.filter(category__id=category_id)
    if search:
        all_games = all_games.filter(name__icontains=search)

    return render_with_notifs(request, 'games.html', {
        'games': all_games,
        'categories': categories,
        'selected_category': category_id,
        'search': search,
    })

# ─── Game Detail ────────────────────────────────────────────────────────────────
def game_detail(request, game_id):
    game = get_object_or_404(Game.objects.select_related('category', 'city', 'provider'), id=game_id)
    user = get_logged_in_user(request)

    if request.method == 'POST':
        if not user:
            messages.warning(request, 'Please login to submit a review.')
            return redirect('login')

        rating = request.POST.get('rating', '5')
        comment = request.POST.get('comment', '').strip()

        if comment:
            Reviews.objects.create(
                user=user,
                game=game,
                rating=float(rating),
                comment=comment
            )
            messages.success(request, 'Thank you! Your review has been submitted and featured on the home screen.')
            return redirect('game_detail', game_id=game_id)

    game_images = GameImages.objects.filter(game=game)
    reviews = Reviews.objects.filter(game=game).select_related('user').order_by('-timestamp')
    avg_rating = 0
    if reviews.exists():
        avg_rating = round(sum(r.rating for r in reviews) / reviews.count(), 1)

    return render_with_notifs(request, 'game_detail.html', {
        'game': game,
        'game_images': game_images,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })

# ─── Categories ─────────────────────────────────────────────────────────────────
def categories(request):
    all_cats = Category.objects.all()
    return render_with_notifs(request, 'categories.html', {
        'categories': all_cats,
    })

import re

# ─── Google OAuth Login Simulation ─────────────────────────────────────────────
def google_login(request):
    email = request.GET.get('email', 'google.user@sparkzone.in')
    name = request.GET.get('name', 'Google Gamer')

    name_parts = name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else 'User'

    user, created = User.objects.get_or_create(
        email=email.lower().strip(),
        defaults={
            'firstName': first_name,
            'lastName': last_name,
            'password': hashlib.sha256('GoogleOAuthSecret123'.encode()).hexdigest(),
            'role': 'user'
        }
    )

    request.session['user_id'] = user.id
    messages.success(request, f'Successfully signed in with Google as {user.firstName}!')
    if user.role == 'provider':
        return redirect('provider_dashboard')
    return redirect('index')

# ─── Register ───────────────────────────────────────────────────────────────────
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

        # Strict Email Format Validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            messages.error(request, 'Please enter a valid email address (e.g. name@domain.com).')
            return render_with_notifs(request, 'register.html', {'cities': cities})

        # Strict 10-Digit Mobile Number Validation for Providers
        if role == 'provider' or phone_val:
            if not re.match(r'^\d{10}$', phone_val):
                messages.error(request, 'Mobile number must be exactly 10 digits.')
                return render_with_notifs(request, 'register.html', {'cities': cities})

        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return render_with_notifs(request, 'register.html', {'cities': cities})

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if role == 'provider':
                has_prof = hasattr(existing_user, 'provider_profile') and existing_user.provider_profile is not None
                if not has_prof:
                    businessName = request.POST.get('businessName', '').strip() or f"{existing_user.firstName}'s Gaming Center"
                    phone = int(phone_val) if phone_val.isdigit() else 9313858614
                    address = request.POST.get('address', '').strip() or 'CG Road, Navrangpura'
                    city_id = request.POST.get('city')
                    city_obj = City.objects.filter(id=city_id).first() if city_id else cities.first()

                    provider_obj = ProviderProfile.objects.create(
                        user=existing_user,
                        businessName=businessName,
                        phone=phone,
                        address=address,
                        city=city_obj,
                        is_verified=True
                    )
                    existing_user.role = 'provider'
                    existing_user.save(update_fields=['role'])

                    # Auto-assign unassigned games
                    Game.objects.filter(provider__isnull=True).update(provider=provider_obj)

                    messages.success(request, f'Provider profile successfully added to account {email}! Please log in.')
                    return redirect('login')
                else:
                    messages.error(request, 'This email already has an active Provider account!')
                    return render_with_notifs(request, 'register.html', {'cities': cities})
            else:
                messages.error(request, 'Email already registered!')
                return render_with_notifs(request, 'register.html', {'cities': cities})

        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User.objects.create(
            firstName=firstName,
            lastName=lastName,
            email=email,
            password=hashed,
            role=role
        )

        if role == 'provider':
            businessName = request.POST.get('businessName', '').strip() or f"{firstName}'s Gaming Center"
            phone = int(phone_val) if phone_val.isdigit() else 9313858614
            address = request.POST.get('address', '').strip() or 'CG Road, Navrangpura'
            city_id = request.POST.get('city')
            city_obj = City.objects.filter(id=city_id).first() if city_id else cities.first()

            provider_obj = ProviderProfile.objects.create(
                user=user,
                businessName=businessName,
                phone=phone,
                address=address,
                city=city_obj,
                is_verified=True
            )

            # Auto-assign unassigned games
            Game.objects.filter(provider__isnull=True).update(provider=provider_obj)

        messages.success(request, f'Account created successfully, {firstName}! Please log in with your credentials.')
        return redirect('login')

    return render_with_notifs(request, 'register.html', {'cities': cities})

# ─── Login ──────────────────────────────────────────────────────────────────────
def login_view(request):
    logged_user = get_logged_in_user(request)
    if logged_user:
        if logged_user.role == 'provider':
            return redirect('provider_dashboard')
        return redirect('index')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        hashed = hashlib.sha256(password.encode()).hexdigest()

        try:
            user = User.objects.get(email=email, password=hashed)
            request.session['user_id'] = user.id
            messages.success(request, f'Welcome back, {user.firstName}!')
            if user.role == 'provider':
                return redirect('provider_dashboard')
            return redirect('index')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render_with_notifs(request, 'login.html', {})

# ─── Logout ─────────────────────────────────────────────────────────────────────
def logout_view(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully.')
    return redirect('index')

# ─── PROVIDER PANEL VIEWS ──────────────────────────────────────────────────────
@provider_required
def provider_dashboard(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile

    # Ensure unassigned games are linked to this provider profile
    if not Game.objects.filter(provider=provider).exists():
        Game.objects.filter(provider__isnull=True).update(provider=provider)

    games = Game.objects.filter(Q(provider=provider) | Q(provider__isnull=True)).select_related('category', 'city').prefetch_related('slots').order_by('-timestamp')
    
    total_slots_count = Slot.objects.filter(game__provider=provider).count()
    total_bookings_count = Booking.objects.filter(game__provider=provider).count()
    pending_requests_count = Booking.objects.filter(game__provider=provider, status='pending').count()

    total_earnings = sum(
        p.amount for p in Payment.objects.filter(booking__game__provider=provider, paymentStatus='completed')
    )

    return render_with_notifs(request, 'provider/dashboard.html', {
        'provider': provider,
        'games': games,
        'total_slots_count': total_slots_count,
        'total_bookings_count': total_bookings_count,
        'pending_requests_count': pending_requests_count,
        'total_earnings': total_earnings,
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
        description = request.POST.get('description', '').strip()
        address = request.POST.get('address', '').strip()
        pricePerHour = float(request.POST.get('pricePerHour', 200))
        totalSystem = int(request.POST.get('totalSystem', 1))
        availableSystems = int(request.POST.get('availableSystems', 1))
        image_url = request.POST.get('image_url', '').strip()
        operating_hours = request.POST.get('operating_hours', '09:00 AM - 10:00 PM').strip()
        status = request.POST.get('status', 'active')
        image_file = request.FILES.get('image') or request.FILES.get('image_file')

        cat_obj = get_object_or_404(Category, id=category_id)
        city_obj = get_object_or_404(City, id=city_id)

        new_game = Game.objects.create(
            provider=provider,
            category=cat_obj,
            city=city_obj,
            name=name,
            description=description,
            address=address,
            pricePerHour=pricePerHour,
            totalSystem=totalSystem,
            availableSystems=availableSystems,
            image_url=image_url if image_url else None,
            image=image_file if image_file else None,
            operating_hours=operating_hours if operating_hours else '09:00 AM - 10:00 PM',
            status=status
        )

        # Handle Gallery Device Photo Uploads
        gallery_files = request.FILES.getlist('gallery_images')
        for gf in gallery_files:
            GameImages.objects.create(game=new_game, image=gf)

        messages.success(request, f'Gaming Station "{name}" created successfully with photos!')
        return redirect('provider_dashboard')

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
        game.description = request.POST.get('description', '').strip()
        game.address = request.POST.get('address', '').strip()
        game.pricePerHour = float(request.POST.get('pricePerHour', 200))
        game.totalSystem = int(request.POST.get('totalSystem', 1))
        game.availableSystems = int(request.POST.get('availableSystems', 1))
        game.image_url = request.POST.get('image_url', '').strip() or None
        game.operating_hours = request.POST.get('operating_hours', '09:00 AM - 10:00 PM').strip() or '09:00 AM - 10:00 PM'
        game.status = request.POST.get('status', 'active')

        image_file = request.FILES.get('image') or request.FILES.get('image_file')
        if image_file:
            game.image = image_file

        game.save()

        # Handle Gallery Device Photo Uploads
        gallery_files = request.FILES.getlist('gallery_images')
        for gf in gallery_files:
            GameImages.objects.create(game=game, image=gf)

        messages.success(request, f'Station "{game.name}" updated successfully!')
        return redirect('provider_dashboard')

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
        messages.info(request, f'Station "{game.name}" marked inactive to preserve past customer booking history.')
    else:
        game.delete()
        messages.success(request, f'Station deleted successfully.')

    return redirect('provider_dashboard')

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
        messages.success(request, 'New time slot created successfully!')
        return redirect('provider_slot_manage', game_id=game_id)

    slots = Slot.objects.filter(game=game).order_by('slotDate', 'startTime')
    return render_with_notifs(request, 'provider/slots.html', {
        'game': game,
        'slots': slots,
    })

@provider_required
def provider_slot_delete(request, slot_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    slot = get_object_or_404(Slot, id=slot_id, game__provider=provider)
    game_id = slot.game_id

    if Booking.objects.filter(slot=slot).exists():
        slot.status = 'cancelled'
        slot.save()
        messages.warning(request, 'Slot cancelled rather than deleted because customer bookings exist.')
    else:
        slot.delete()
        messages.success(request, 'Time slot deleted successfully.')

    return redirect('provider_slot_manage', game_id=game_id)

# ─── PROVIDER BOOKING REQUESTS ─────────────────────────────────────────────────
@provider_required
def provider_booking_requests(request):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    requests_list = Booking.objects.filter(
        game__provider=provider
    ).select_related('user', 'game', 'slot').order_by('-timestamp')

    return render_with_notifs(request, 'provider/booking_requests.html', {
        'provider': provider,
        'requests': requests_list,
    })

@provider_required
def provider_booking_accept(request, booking_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile

    with db_transaction.atomic():
        booking_obj = get_object_or_404(
            Booking.objects.select_related('game', 'user', 'slot'),
            id=booking_id,
            game__provider=provider
        )

        if booking_obj.status != 'pending':
            messages.warning(request, f'Booking is already {booking_obj.get_status_display()}.')
            return redirect('provider_booking_requests')

        slot_obj = None
        if booking_obj.slot_id:
            slot_obj = Slot.objects.select_for_update().filter(id=booking_obj.slot_id).first()

        if slot_obj:
            if slot_obj.is_full() or slot_obj.bookedCount >= slot_obj.capacity:
                booking_obj.status = 'rejected'
                booking_obj.responded_at = timezone.now()
                booking_obj.save()
                Notification.objects.create(
                    user=booking_obj.user,
                    booking=booking_obj,
                    title="Booking Could Not Be Accepted",
                    message=f"Sorry, the slot for {booking_obj.game.name} on {booking_obj.bookingDate} was filled by another booking."
                )
                messages.error(request, 'Slot capacity is full! Request automatically rejected.')
                return redirect('provider_booking_requests')

            slot_obj.bookedCount += 1
            if slot_obj.bookedCount >= slot_obj.capacity:
                slot_obj.status = 'booked'
            slot_obj.save()

        booking_obj.status = 'accepted'
        booking_obj.responded_at = timezone.now()
        booking_obj.save()

        # Send Notification to Gamer
        Notification.objects.create(
            user=booking_obj.user,
            booking=booking_obj,
            title="Booking Request Accepted! 🎉",
            message=f"Great news! Your booking request for {booking_obj.game.name} on {booking_obj.bookingDate} ({booking_obj.startTime.strftime('%H:%M')}-{booking_obj.endTime.strftime('%H:%M')}) was ACCEPTED by the provider!"
        )

    messages.success(request, f'Booking request for {booking_obj.user.firstName} accepted!')
    return redirect('provider_booking_requests')

@provider_required
def provider_booking_reject(request, booking_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile

    with db_transaction.atomic():
        booking_obj = get_object_or_404(
            Booking.objects.select_related('game', 'user'),
            id=booking_id,
            game__provider=provider
        )

        booking_obj.status = 'rejected'
        booking_obj.responded_at = timezone.now()
        booking_obj.save()

        # Send Notification to Gamer
        Notification.objects.create(
            user=booking_obj.user,
            booking=booking_obj,
            title="Booking Request Update",
            message=f"Your booking request for {booking_obj.game.name} on {booking_obj.bookingDate} was not accepted by the provider."
        )

    messages.info(request, f'Booking request for {booking_obj.user.firstName} rejected.')
    return redirect('provider_booking_requests')

# ─── Booking ────────────────────────────────────────────────────────────────────
def booking(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    user = get_logged_in_user(request)
    if not user:
        messages.warning(request, 'Please login to make a booking.')
        return redirect('login')

    if request.method == 'POST':
        bookingDate = request.POST.get('bookingDate')
        startTime = request.POST.get('startTime')
        endTime = request.POST.get('endTime')
        paymentMethod = request.POST.get('paymentMethod', 'credit_card')
        slot_id = request.POST.get('slot_id')

        from datetime import datetime
        fmt = '%H:%M'
        start = datetime.strptime(startTime, fmt)
        end = datetime.strptime(endTime, fmt)
        hours = (end - start).seconds / 3600
        if hours <= 0:
            messages.error(request, 'End time must be after start time.')
            return redirect('booking', game_id=game_id)

        with db_transaction.atomic():
            slot_obj = None
            if slot_id:
                slot_obj = Slot.objects.select_for_update().filter(id=slot_id, game=game).first()
                if slot_obj:
                    if slot_obj.is_full():
                        messages.error(request, 'Sorry, this slot is already fully booked! Please select another time slot.')
                        return redirect('booking', game_id=game_id)

                    # Prevent duplicate pending request by same user for same slot
                    if Booking.objects.filter(user=user, slot=slot_obj, status__in=['pending', 'accepted', 'confirmed']).exists():
                        messages.warning(request, 'You already have an active booking request for this time slot.')
                        return redirect('my_bookings')

            price_per_hr = slot_obj.get_price() if slot_obj else game.pricePerHour
            totalAmount = hours * price_per_hr

            booking_obj = Booking.objects.create(
                user=user,
                game=game,
                slot=slot_obj,
                bookingDate=bookingDate,
                startTime=startTime,
                endTime=endTime,
                totalAmount=totalAmount,
                status='pending',
            )

            Payment.objects.create(
                user=user,
                booking=booking_obj,
                amount=totalAmount,
                paymentMethod=paymentMethod,
                paymentStatus='completed'
            )

            # Notify Provider
            if game.provider and hasattr(game.provider, 'user'):
                Notification.objects.create(
                    user=game.provider.user,
                    booking=booking_obj,
                    title="New Booking Request 🎮",
                    message=f"{user.firstName} {user.lastName} requested to book {game.name} on {bookingDate} ({startTime}-{endTime})."
                )

        messages.success(request, 'Your booking request has been submitted and is pending provider approval!')
        return redirect('my_bookings')

    available_slots = Slot.objects.filter(game=game, status='available').order_by('slotDate', 'startTime')
    return render_with_notifs(request, 'booking.html', {
        'game': game,
        'available_slots': available_slots,
    })

# ─── Cancel Booking (Gamer) ─────────────────────────────────────────────────────
def cancel_booking(request, booking_id):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    with db_transaction.atomic():
        booking_obj = get_object_or_404(Booking, id=booking_id, user=user)

        if booking_obj.status in ['cancelled', 'rejected']:
            messages.info(request, f'Booking is already {booking_obj.get_status_display()}.')
            return redirect('my_bookings')

        # If previously accepted, free up slot capacity
        if booking_obj.status in ['accepted', 'confirmed'] and booking_obj.slot_id:
            slot_obj = Slot.objects.select_for_update().filter(id=booking_obj.slot_id).first()
            if slot_obj:
                slot_obj.bookedCount = max(0, slot_obj.bookedCount - 1)
                if slot_obj.bookedCount < slot_obj.capacity and slot_obj.status == 'booked':
                    slot_obj.status = 'available'
                slot_obj.save()

        booking_obj.status = 'cancelled'
        booking_obj.save()

        # Notify Provider
        if booking_obj.game.provider and hasattr(booking_obj.game.provider, 'user'):
            Notification.objects.create(
                user=booking_obj.game.provider.user,
                booking=booking_obj,
                title="Booking Cancelled",
                message=f"{user.firstName} cancelled their booking request for {booking_obj.game.name} on {booking_obj.bookingDate}."
            )

    messages.success(request, 'Booking request cancelled successfully.')
    return redirect('my_bookings')

# ─── My Bookings ────────────────────────────────────────────────────────────────
def my_bookings(request):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    bookings = list(Booking.objects.filter(user=user).select_related('game', 'game__category').order_by('-timestamp'))
    payments = {p.booking_id: p for p in Payment.objects.filter(booking__in=bookings)}
    for b in bookings:
        b.payment_info = payments.get(b.id)

    return render_with_notifs(request, 'my_bookings.html', {
        'bookings': bookings,
    })

# ─── Contact ────────────────────────────────────────────────────────────────────
def contact(request):
    if request.method == 'POST':
        ContactUs.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            message=request.POST.get('message'),
        )
        messages.success(request, 'Your message has been sent! We will get back to you soon.')
        return redirect('contact')

    return render_with_notifs(request, 'contact.html', {})
