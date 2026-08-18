from django.utils.safestring import mark_safe
from django.db import models

class User(models.Model):
    ROLE_CHOICES = [
        ('user', 'Gamer / Customer'),
        ('provider', 'Gaming Center Provider'),
    ]
    firstName = models.CharField(max_length=60)
    lastName = models.CharField(max_length=60)
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', db_index=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.firstName} {self.lastName} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.firstName} {self.lastName}".strip()

    def is_provider(self):
        return self.role == 'provider'

class Country(models.Model):
    name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name

class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name

class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    phone = models.BigIntegerField()
    address = models.TextField()
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name='user_profiles')
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name='user_profiles')
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='user_profiles')
    profile = models.ImageField(upload_to="Users", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def UserImage(self):
        if self.profile:
            return mark_safe('<img src={} width="200px">'.format(self.profile.url))
        return mark_safe('<span>No Image</span>')

class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    businessName = models.CharField(max_length=120)
    phone = models.BigIntegerField()
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='providers')
    is_verified = models.BooleanField(default=True, db_index=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return self.businessName

DEFAULT_GAMING_IMAGE = "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=640&q=75"
DEFAULT_CATEGORY_IMAGE = "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=640&q=75"

class Category(models.Model):
    categoryName = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="Category", null=True, blank=True)
    image_url = models.URLField(max_length=2000, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return self.categoryName

    def get_image_url(self):
        if self.image:
            try:
                if hasattr(self.image.storage, 'exists') and not self.image.storage.exists(self.image.name):
                    if self.image_url:
                        return self.image_url
                    return DEFAULT_CATEGORY_IMAGE
                return self.image.url
            except Exception:
                pass
        if self.image_url:
            url = self.image_url
            if 'images.unsplash.com' in url and 'auto=format' not in url:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}auto=format&fit=crop&w=400&q=60"
            return url
        return DEFAULT_CATEGORY_IMAGE

    def get_image_srcset(self):
        url = self.get_image_url()
        if url and 'images.unsplash.com' in url:
            base = url.split('?')[0]
            return f"{base}?auto=format&fit=crop&w=360&q=60 360w, {base}?auto=format&fit=crop&w=480&q=60 480w"
        return ""

    def categoryImage(self):
        url = self.get_image_url()
        if url:
            return mark_safe('<img src={} width="200px">'.format(url))
        return mark_safe('<span>No Image</span>')

class Game(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    provider = models.ForeignKey(ProviderProfile, on_delete=models.PROTECT, null=True, blank=True, related_name='games')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='games')
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='games')
    pricePerHour = models.FloatField(db_index=True)
    totalSystem = models.IntegerField(default=1)
    availableSystems = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    image = models.ImageField(upload_to="Game", null=True, blank=True)
    image_url = models.URLField(max_length=2000, null=True, blank=True)
    available_games = models.TextField(null=True, blank=True, help_text="Comma-separated names of games available at this station")
    operating_hours = models.CharField(max_length=100, default="09:00 AM - 10:00 PM", null=True, blank=True)
    out_of_service_units = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated unit numbers out of service e.g. 2,5")
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return self.name

    def get_disabled_units_set(self):
        if not self.out_of_service_units:
            return set()
        res = set()
        for item in self.out_of_service_units.split(','):
            item = item.strip()
            if item.isdigit():
                res.add(int(item))
        return res

    def get_games_list(self):
        if not self.available_games:
            return []
        return [g.strip() for g in self.available_games.split(',') if g.strip()]

    def get_image_url(self):
        if self.image:
            try:
                if hasattr(self.image.storage, 'exists') and not self.image.storage.exists(self.image.name):
                    if self.image_url:
                        return self.image_url
                    return DEFAULT_GAMING_IMAGE
                return self.image.url
            except Exception:
                pass
        if self.image_url:
            url = self.image_url
            if 'images.unsplash.com' in url and 'auto=format' not in url:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}auto=format&fit=crop&w=400&q=60"
            return url
        return DEFAULT_GAMING_IMAGE

    def get_image_srcset(self):
        url = self.get_image_url()
        if url and 'images.unsplash.com' in url:
            base = url.split('?')[0]
            return f"{base}?auto=format&fit=crop&w=360&q=60 360w, {base}?auto=format&fit=crop&w=480&q=60 480w"
        return ""

    def GameImage(self):
        url = self.get_image_url()
        if url:
            return mark_safe('<img src={} width="200px">'.format(url))
        return mark_safe('<span>No Image</span>')

class Slot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Fully Booked'),
        ('cancelled', 'Cancelled')
    ]
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='slots')
    slotDate = models.DateField(db_index=True)
    startTime = models.TimeField()
    endTime = models.TimeField()
    capacity = models.IntegerField(default=1)
    bookedCount = models.IntegerField(default=0)
    price = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_index=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.game.name} - {self.slotDate} ({self.startTime.strftime('%H:%M')}-{self.endTime.strftime('%H:%M')})"

    def get_price(self):
        if self.price is not None:
            return self.price
        return self.game.pricePerHour

    def is_full(self, start_time=None, end_time=None):
        if self.status == 'cancelled':
            return True
        if start_time and end_time:
            overlapping_count = self.bookings.filter(
                status__in=['pending', 'accepted', 'confirmed'],
                startTime__lt=end_time,
                endTime__gt=start_time
            ).count()
            return overlapping_count >= self.capacity
        if self.status == 'booked':
            return True
        return self.bookedCount >= self.capacity

class GameImages(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="Games")

    def GameImage(self):
        if self.image:
            return mark_safe('<img src={} width="200px">'.format(self.image.url))
        return mark_safe('<span>No Image</span>')

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='bookings')
    slot = models.ForeignKey(Slot, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    bookingDate = models.DateField(db_index=True)
    startTime = models.TimeField()
    endTime = models.TimeField()
    totalAmount = models.FloatField()
    status = models.CharField(max_length=60, choices=STATUS_CHOICES, default='pending', db_index=True)
    unit_number = models.IntegerField(null=True, blank=True, help_text="Specific unit/console number (1..N)")
    unit_numbers = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated unit numbers e.g. 4,5")
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.user.firstName} {self.user.lastName} / {self.game.name} / {self.get_status_display()}"

    def get_unit_numbers_list(self):
        if self.unit_numbers:
            res = []
            for item in self.unit_numbers.split(','):
                item = item.strip()
                if item.isdigit():
                    res.append(int(item))
            if res:
                return res
        if self.unit_number:
            return [self.unit_number]
        return []

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.user.firstName} - {self.title} ({'Read' if self.is_read else 'Unread'})"

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('other', 'Other')
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.FloatField()
    paymentMethod = models.CharField(max_length=60, choices=PAYMENT_METHOD_CHOICES, db_index=True)
    paymentStatus = models.CharField(max_length=60, choices=PAYMENT_STATUS_CHOICES, default='completed', db_index=True)
    paymentDate = models.DateTimeField(auto_now=True, db_index=True)

class Reviews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='reviews')
    rating = models.FloatField(db_index=True)
    comment = models.TextField()
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

class ContactUs(models.Model):
    name = models.CharField(max_length=60)
    email = models.EmailField(db_index=True)
    phone = models.BigIntegerField()
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now=True, db_index=True)
