from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *
import hashlib

# ─── Helper ────────────────────────────────────────────────────────────────────
def get_logged_in_user(request):
    uid = request.session.get('user_id')
    if uid:
        try:
            return User.objects.get(id=uid)
        except User.DoesNotExist:
            pass
    return None

# ─── Home ───────────────────────────────────────────────────────────────────────
def index(request):
    categories = Category.objects.all()
    games = Game.objects.select_related('category', 'city').all()[:6]
    reviews = Reviews.objects.select_related('user', 'game').all()[:6]
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
    all_games = Game.objects.select_related('category', 'city').all()
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
    game = get_object_or_404(Game, id=game_id)
    game_images = GameImages.objects.filter(game=game)
    reviews = Reviews.objects.filter(game=game).select_related('user')
    avg_rating = 0
    if reviews.exists():
        avg_rating = round(sum(r.rating for r in reviews) / reviews.count(), 1)
    user = get_logged_in_user(request)
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
    if request.method == 'POST':
        firstName = request.POST.get('firstName')
        lastName = request.POST.get('lastName')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('register')

        hashed = hashlib.sha256(password.encode()).hexdigest()
        user = User.objects.create(firstName=firstName, lastName=lastName, email=email, password=hashed)
        request.session['user_id'] = user.id
        messages.success(request, f'Welcome, {firstName}! Account created successfully.')
        return redirect('index')

    return render(request, 'register.html', {'logged_in_user': None})

# ─── Login ──────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        hashed = hashlib.sha256(password.encode()).hexdigest()

        try:
            user = User.objects.get(email=email, password=hashed)
            request.session['user_id'] = user.id
            messages.success(request, f'Welcome back, {user.firstName}!')
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

        # Calculate total hours & amount
        from datetime import datetime
        fmt = '%H:%M'
        start = datetime.strptime(startTime, fmt)
        end = datetime.strptime(endTime, fmt)
        hours = (end - start).seconds / 3600
        if hours <= 0:
            messages.error(request, 'End time must be after start time.')
            return redirect('booking', game_id=game_id)

        totalAmount = hours * game.pricePerHour

        booking_obj = Booking.objects.create(
            user=user,
            game=game,
            bookingDate=bookingDate,
            startTime=startTime,
            endTime=endTime,
            totalAmount=totalAmount,
            status='pending',
        )
        messages.success(request, f'Booking confirmed! Total: ₹{totalAmount:.2f}')
        return redirect('my_bookings')

    return render(request, 'booking.html', {
        'game': game,
        'logged_in_user': user,
    })

# ─── My Bookings ────────────────────────────────────────────────────────────────
def my_bookings(request):
    user = get_logged_in_user(request)
    if not user:
        return redirect('login')

    bookings = Booking.objects.filter(user=user).select_related('game').order_by('-timestamp')
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
