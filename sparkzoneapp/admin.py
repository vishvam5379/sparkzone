from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(User)
class ShowUsers(admin.ModelAdmin):
    list_display = ["firstName", "lastName", "email", "timestamp"]
    list_filter = ["timestamp"]
    search_fields = ["firstName", "lastName"]
    list_per_page = 2
    list_display_links = ["firstName","lastName"]

@admin.register(Country)
class ShowCountry(admin.ModelAdmin):
    list_display = ["name"]

@admin.register(State)
class ShowState(admin.ModelAdmin):
    list_display = ["country", "name"]

@admin.register(City)
class ShowCity(admin.ModelAdmin):
    list_display = ["state", "name"]

@admin.register(UserProfile)
class ShowUserProfile(admin.ModelAdmin):
    list_display = ["user", "phone", "address", "country", "state", "city", "profile", "UserImage", "timestamp"]
    search_fields = ["state__name", "timestamp"]


@admin.register(Category)
class ShowCategory(admin.ModelAdmin):
    list_display = ["categoryName", "description", "image", "categoryImage", "timestamp"]

@admin.register(Game)
class ShowGame(admin.ModelAdmin):
    list_display = ["category", "name", "address", "city", "pricePerHour", "totalSystem", "availableSystems", "image", "GameImage", "timestamp"]
    list_filter = ["category__categoryName"]
    list_editable = ["availableSystems", "image"]


@admin.register(GameImages)
class ShowGameImages(admin.ModelAdmin):
    list_display = ["game", "image", "GameImage"]

@admin.register(Booking)
class ShowBooking(admin.ModelAdmin):
    list_display = ["user", "game", "bookingDate", "startTime", "endTime", "totalAmount", "status", "timestamp"]

@admin.register(Payment)
class ShowPayments(admin.ModelAdmin):
    list_display = ["user", "booking", "amount", "paymentMethod", "paymentStatus", "paymentDate"]
    list_filter = ["paymentMethod", "paymentStatus"]

@admin.register(Reviews)
class ShowReviews(admin.ModelAdmin):
    list_display = ["user", "game", "rating", "comment", "timestamp"]

@admin.register(ContactUs)
class ShowContacts(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "message", "timestamp"]