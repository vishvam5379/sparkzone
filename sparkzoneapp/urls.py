from django.urls import path
from . import views

urlpatterns = [
    # Marketplace & Discovery (Gamer)
    path('', views.index, name='index'),
    path('stations/', views.games, name='games'),
    path('stations/<int:game_id>/', views.game_detail, name='game_detail'),
    path('games/', views.games, name='games_legacy'),
    path('games/<int:game_id>/', views.game_detail, name='game_detail_legacy'),
    path('categories/', views.categories, name='categories'),
    
    # Booking & Payment (Instant Lock & Razorpay)
    path('checkout/<int:game_id>/', views.gamer_checkout, name='gamer_checkout'),
    path('booking/<int:game_id>/', views.gamer_checkout, name='booking'),
    path('payment/verify/', views.razorpay_verify, name='razorpay_verify'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('favorites/toggle/<int:game_id>/', views.api_toggle_favorite, name='api_toggle_favorite'),
    path('reviews/submit/<int:booking_id>/', views.submit_review, name='submit_review'),

    # Gamer Dashboard & Passes
    path('dashboard/gamer/', views.gamer_dashboard, name='gamer_dashboard'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('google-login/', views.google_login, name='google_login'),
    path('logout/', views.logout_view, name='logout'),

    # Provider Operations Panel
    path('dashboard/provider/', views.provider_dashboard, name='provider_dashboard'),
    path('provider/dashboard/', views.provider_dashboard, name='provider_dashboard_legacy'),
    path('provider/stations/', views.provider_stations, name='provider_stations'),
    path('provider/games/add/', views.provider_game_add, name='provider_game_add'),
    path('provider/games/<int:game_id>/edit/', views.provider_game_edit, name='provider_game_edit'),
    path('provider/games/<int:game_id>/delete/', views.provider_game_delete, name='provider_game_delete'),
    path('provider/slots/<int:game_id>/', views.provider_slot_manage, name='provider_slot_manage'),
    path('provider/slots/<int:game_id>/bulk-generate/', views.provider_slot_bulk_generate, name='provider_slot_bulk_generate'),
    path('provider/slots/<int:slot_id>/delete/', views.provider_slot_delete, name='provider_slot_delete'),
    path('provider/bookings/', views.provider_bookings, name='provider_bookings'),
    path('provider/requests/', views.provider_bookings, name='provider_booking_requests'),
    path('provider/bookings/<int:booking_id>/checkin/', views.provider_booking_checkin, name='provider_booking_checkin'),
    path('provider/bookings/<int:booking_id>/noshow/', views.provider_booking_noshow, name='provider_booking_noshow'),

    # Superadmin Platform Portal
    path('admin-portal/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('admin-portal/verify-venue/<int:provider_id>/', views.superadmin_toggle_verify, name='superadmin_toggle_verify'),

    # Real-Time APIs & General
    path('api/unit-availability/<int:game_id>/', views.get_unit_availability_api, name='get_unit_availability_api'),
    path('api/provider/toggle-unit-maintenance/<int:game_id>/', views.provider_toggle_unit_maintenance_api, name='provider_toggle_unit_maintenance_api'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('health/', views.health_check, name='health_check'),
    path('contact/', views.contact, name='contact'),
]
