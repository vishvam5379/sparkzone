from django.utils.safestring import mark_safe
from django.db import models

# Create your models here.
class User(models.Model):
    firstName = models.CharField(max_length=60)
    lastName = models.CharField(max_length=60)
    email = models.EmailField()
    password = models.CharField(max_length=60)
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.firstName} {self.lastName}"

class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class City(models.Model):
    state = models. ForeignKey(State, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    phone = models.BigIntegerField()
    address = models.TextField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    profile = models.ImageField(upload_to="Users")
    timestamp = models.DateTimeField(auto_now=True)

    def UserImage(self):
        return mark_safe('<img src={} width="200px">'.format(self.profile.url))

class Category(models.Model):
    categoryName = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="Category")
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.categoryName

    def categoryImage(self):
        return mark_safe('<img src={} width="200px">'.format(self.image.url))


class Game(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    pricePerHour = models.FloatField()
    totalSystem = models.IntegerField()
    availableSystems = models.IntegerField()
    image = models.ImageField(upload_to="Game")
    timestamp = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name

    def GameImage(self):
        return mark_safe('<img src={} width="200px">'.format(self.image.url))


class GameImages(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="Games")

    def GameImage(self):
        return mark_safe('<img src={} width="200px">'.format(self.image.url))


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    bookingDate = models.DateField()
    startTime = models.TimeField()
    endTime = models.TimeField()
    totalAmount = models.FloatField()
    status = models.CharField(max_length=60, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')])
    timestamp = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.user.firstName} {self.user.lastName} / {self.startTime}-{self.endTime} / {self.totalAmount}"


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    amount = models.FloatField()
    paymentMethod = models.CharField(max_length=60, choices=[('credit_card', 'Credit Card'), ('debit_card', 'Debit Card'), ('paypal', 'PayPal'), ('other', 'Other')])
    paymentStatus = models.CharField(max_length=60, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')])
    paymentDate = models.DateTimeField(auto_now=True)


class Reviews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    rating = models.FloatField()
    comment = models.TextField()
    timestamp = models.DateTimeField(auto_now=True)


class ContactUs(models.Model):
    name = models.CharField(max_length=60)
    email = models.EmailField()
    phone = models.BigIntegerField()
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now=True)
