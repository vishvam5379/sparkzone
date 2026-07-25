from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import *

# Register your models here.
@admin.register(User)
class ShowUsers(ModelAdmin):
    list_display = ["firstName", "lastName", "email", "timestamp"]
    list_filter = ["timestamp"]
    search_fields = ["firstName", "lastName"]
    list_per_page = 10
    list_display_links = ["firstName","lastName"]

@admin.register(Country)
class ShowCountry(ModelAdmin):
    list_display = ["name"]

@admin.register(State)
class ShowState(ModelAdmin):
    list_display = ["country", "name"]

@admin.register(City)
class ShowCity(ModelAdmin):
    list_display = ["state", "name"]

@admin.register(UserProfile)
class ShowUserProfile(ModelAdmin):
    list_display = ["user", "phone", "address", "country", "state", "city", "profile", "UserImage", "timestamp"]
    search_fields = ["state__name", "timestamp"]

@admin.register(Category)
class ShowCategory(ModelAdmin):
    list_display = ["categoryName", "description", "image", "categoryImage", "timestamp"]

@admin.register(Game)
class ShowGame(ModelAdmin):
    list_display = ["category", "name", "address", "city", "pricePerHour", "totalSystem", "availableSystems", "image", "GameImage", "timestamp"]
    list_filter = ["category__categoryName"]
    list_editable = ["availableSystems", "image"]

@admin.register(GameImages)
class ShowGameImages(ModelAdmin):
    list_display = ["game", "image", "GameImage"]

@admin.register(Booking)
class ShowBooking(ModelAdmin):
    list_display = ["user", "game", "bookingDate", "startTime", "endTime", "totalAmount", "status", "timestamp"]

@admin.register(Payment)
class ShowPayments(ModelAdmin):
    list_display = ["user", "booking", "amount", "paymentMethod", "paymentStatus", "paymentDate"]
    list_filter = ["paymentMethod", "paymentStatus"]

@admin.register(Reviews)
class ShowReviews(ModelAdmin):
    list_display = ["user", "game", "rating", "comment", "timestamp"]

@admin.register(ContactUs)
class ShowContacts(ModelAdmin):
    list_display = ["name", "email", "phone", "message", "timestamp"]