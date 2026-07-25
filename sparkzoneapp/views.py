from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection
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

def provider_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_logged_in_user(request)
        if not user or user.role != 'provider' or not hasattr(user, 'provider_profile'):
            messages.error(request, 'Access denied. Provider account required.')
            return redirect('login')
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
    user = get_logged_in_user(request)
    return render(request, 'index.html', {
        'categories': categories,
        'games': games,
        'reviews': reviews,
        'logged_in_user': user,
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

    user = get_logged_in_user(request)
    return render(request, 'games.html', {
        'games': all_games,
        'categories': categories,
        'selected_category': category_id,
        'search': search,
        'logged_in_user': user,
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

    return render(request, 'game_detail.html', {
        'game': game,
        'game_images': game_images,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'logged_in_user': user,
    })

# ─── Categories ─────────────────────────────────────────────────────────────────
def categories(request):
    all_cats = Category.objects.all()
    user = get_logged_in_user(request)
    return render(request, 'categories.html', {
        'categories': all_cats,
        'logged_in_user': user,
    })

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

        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'register.html', {'cities': cities, 'logged_in_user': None})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'register.html', {'cities': cities, 'logged_in_user': None})

        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User.objects.create(
            firstName=firstName,
            lastName=lastName,
            email=email,
            password=hashed,
            role=role
        )

        if role == 'provider':
            businessName = request.POST.get('businessName', f"{firstName}'s Gaming Center").strip()
            phone = request.POST.get('phone', '9876543210')
            address = request.POST.get('address', 'Main Street').strip()
            city_id = request.POST.get('city')
            city_obj = City.objects.filter(id=city_id).first() if city_id else cities.first()

            ProviderProfile.objects.create(
                user=user,
                businessName=businessName,
                phone=int(phone) if phone.isdigit() else 9876543210,
                address=address,
                city=city_obj,
                is_verified=True
            )

        messages.success(request, f'Account created successfully, {firstName}! Please log in with your credentials.')
        return redirect('login')

    return render(request, 'register.html', {'cities': cities, 'logged_in_user': None})

# ─── Login ──────────────────────────────────────────────────────────────────────
def login_view(request):
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

    return render(request, 'login.html', {'logged_in_user': None})

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
    games = Game.objects.filter(provider=provider).select_related('category', 'city').prefetch_related('slots').order_by('-timestamp')
    
    total_slots_count = Slot.objects.filter(game__provider=provider).count()
    total_bookings_count = Booking.objects.filter(game__provider=provider).count()

    total_earnings = sum(
        p.amount for p in Payment.objects.filter(booking__game__provider=provider, paymentStatus='completed')
    )

    return render(request, 'provider/dashboard.html', {
        'provider': provider,
        'games': games,
        'total_slots_count': total_slots_count,
        'total_bookings_count': total_bookings_count,
        'total_earnings': total_earnings,
        'logged_in_user': user,
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
        status = request.POST.get('status', 'active')

        cat_obj = get_object_or_404(Category, id=category_id)
        city_obj = get_object_or_404(City, id=city_id)

        Game.objects.create(
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
            status=status
        )
        messages.success(request, f'Gaming Station "{name}" created successfully!')
        return redirect('provider_dashboard')

    return render(request, 'provider/game_form.html', {
        'is_edit': False,
        'categories': categories,
        'cities': cities,
        'logged_in_user': user,
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
        game.status = request.POST.get('status', 'active')
        game.save()

        messages.success(request, f'Station "{game.name}" updated successfully!')
        return redirect('provider_dashboard')

    return render(request, 'provider/game_form.html', {
        'is_edit': True,
        'game': game,
        'categories': categories,
        'cities': cities,
        'logged_in_user': user,
    })

@provider_required
def provider_game_delete(request, game_id):
    user = get_logged_in_user(request)
    provider = user.provider_profile
    game = get_object_or_404(Game, id=game_id, provider=provider)
    
    # Soft delete / toggle inactive if bookings exist, else delete
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
    return render(request, 'provider/slots.html', {
        'game': game,
        'slots': slots,
        'logged_in_user': user,
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

        slot_obj = Slot.objects.filter(id=slot_id, game=game).first() if slot_id else None

        from datetime import datetime
        fmt = '%H:%M'
        start = datetime.strptime(startTime, fmt)
        end = datetime.strptime(endTime, fmt)
        hours = (end - start).seconds / 3600
        if hours <= 0:
            messages.error(request, 'End time must be after start time.')
            return redirect('booking', game_id=game_id)

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

        method_labels = {
            'credit_card': 'Credit Card',
            'upi': 'UPI',
            'bank_transfer': 'Bank Transfer',
            'debit_card': 'Debit Card',
            'paypal': 'PayPal',
            'other': 'Other'
        }
        method_name = method_labels.get(paymentMethod, 'Selected Method')
        messages.success(request, f'Booking confirmed via {method_name}! Total: ₹{totalAmount:.2f}')
        return redirect('my_bookings')

    available_slots = Slot.objects.filter(game=game, status='available').order_by('slotDate', 'startTime')
    return render(request, 'booking.html', {
        'game': game,
        'available_slots': available_slots,
        'logged_in_user': user,
    })

# ─── My Bookings ────────────────────────────────────────────────────────────────
def my_bookings(request):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    bookings = list(Booking.objects.filter(user=user).select_related('game', 'game__category').order_by('-timestamp'))
    payments = {p.booking_id: p for p in Payment.objects.filter(booking__in=bookings)}
    for b in bookings:
        b.payment_info = payments.get(b.id)

    return render(request, 'my_bookings.html', {
        'bookings': bookings,
        'logged_in_user': user,
    })

# ─── Contact ────────────────────────────────────────────────────────────────────
def contact(request):
    user = get_logged_in_user(request)
    if request.method == 'POST':
        ContactUs.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            message=request.POST.get('message'),
        )
        messages.success(request, 'Your message has been sent! We will get back to you soon.')
        return redirect('contact')

    return render(request, 'contact.html', {'logged_in_user': user})
