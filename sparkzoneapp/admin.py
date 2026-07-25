from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import *

@admin.register(User)
class ShowUsers(ModelAdmin):
    list_display = ["firstName", "lastName", "email", "role", "timestamp"]
    list_filter = ["role", "timestamp"]
    search_fields = ["firstName", "lastName", "email"]
    list_per_page = 15
    list_display_links = ["firstName", "lastName"]

@admin.register(ProviderProfile)
class ShowProviderProfile(ModelAdmin):
    list_display = ["businessName", "user", "phone", "city", "is_verified", "timestamp"]
    list_filter = ["is_verified", "city"]
    search_fields = ["businessName", "user__firstName", "user__email"]
    list_editable = ["is_verified"]

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
    list_display = ["name", "provider", "category", "city", "pricePerHour", "totalSystem", "availableSystems", "status", "timestamp"]
    list_filter = ["status", "category__categoryName", "city"]
    list_editable = ["status", "availableSystems"]
    search_fields = ["name", "address"]

@admin.register(Slot)
class ShowSlot(ModelAdmin):
    list_display = ["game", "slotDate", "startTime", "endTime", "capacity", "bookedCount", "price", "status", "timestamp"]
    list_filter = ["status", "slotDate", "game"]
    list_editable = ["status"]

@admin.register(GameImages)
class ShowGameImages(ModelAdmin):
    list_display = ["game", "image", "GameImage"]

@admin.register(Booking)
class ShowBooking(ModelAdmin):
    list_display = ["user", "game", "slot", "bookingDate", "startTime", "endTime", "totalAmount", "status", "timestamp"]
    list_filter = ["status", "bookingDate"]

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