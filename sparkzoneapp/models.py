from django.utils.safestring import mark_safe
from django.db import models

class User(models.Model):
    firstName = models.CharField(max_length=60)
    lastName = models.CharField(max_length=60)
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.firstName} {self.lastName}"

    def get_full_name(self):
        return f"{self.firstName} {self.lastName}".strip()

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

class Category(models.Model):
    categoryName = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    image = models.ImageField(upload_to="Category", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return self.categoryName

    def categoryImage(self):
        if self.image:
            return mark_safe('<img src={} width="200px">'.format(self.image.url))
        return mark_safe('<span>No Image</span>')

class Game(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='games')
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='games')
    pricePerHour = models.FloatField(db_index=True)
    totalSystem = models.IntegerField(default=1)
    availableSystems = models.IntegerField(default=1)
    image = models.ImageField(upload_to="Game", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return self.name

    def GameImage(self):
        if self.image:
            return mark_safe('<img src={} width="200px">'.format(self.image.url))
        return mark_safe('<span>No Image</span>')

class GameImages(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="Games")

    def GameImage(self):
        if self.image:
            return mark_safe('<img src={} width="200px">'.format(self.image.url))
        return mark_safe('<span>No Image</span>')

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='bookings')
    bookingDate = models.DateField(db_index=True)
    startTime = models.TimeField()
    endTime = models.TimeField()
    totalAmount = models.FloatField()
    status = models.CharField(max_length=60, choices=STATUS_CHOICES, default='pending', db_index=True)
    timestamp = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.user.firstName} {self.user.lastName} / {self.startTime}-{self.endTime} / ₹{self.totalAmount}"

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
