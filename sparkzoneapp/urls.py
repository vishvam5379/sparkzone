from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('games/', views.games, name='games'),
    path('games/<int:game_id>/', views.game_detail, name='game_detail'),
    path('categories/', views.categories, name='categories'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('booking/<int:game_id>/', views.booking, name='booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('contact/', views.contact, name='contact'),
    path('health/', views.health_check, name='health_check'),

    # Provider Panel Routes
    path('provider/dashboard/', views.provider_dashboard, name='provider_dashboard'),
    path('provider/games/add/', views.provider_game_add, name='provider_game_add'),
    path('provider/games/<int:game_id>/edit/', views.provider_game_edit, name='provider_game_edit'),
    path('provider/games/<int:game_id>/delete/', views.provider_game_delete, name='provider_game_delete'),
    path('provider/games/<int:game_id>/slots/', views.provider_slot_manage, name='provider_slot_manage'),
    path('provider/slots/<int:slot_id>/delete/', views.provider_slot_delete, name='provider_slot_delete'),
]
