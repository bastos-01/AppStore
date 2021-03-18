import datetime

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
# Create your models here.
from django.db.models import Min, Avg
from django.db.models.functions import Ceil


class Developer(models.Model):
    name = models.CharField(max_length=50,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return  str(self.name)

class Category(models.Model):
    title = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return str(self.title)


class Product(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.URLField()
    description = models.CharField(max_length=150)
    category = models.ManyToManyField(Category)
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    'The default plan of a Product will be its plan with the lowest price'

    @property
    def price(self):
        return round(Product_Pricing_Plan.objects.filter(product=self).aggregate(Min('price'))['price__min'],2)

    @property
    def stars(self):
        stars = Reviews.objects.filter(product=self).aggregate(rating__avg=Ceil(Avg('rating')))['rating__avg']
        if stars is None:
            stars = 0
        return int(stars)


class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    favorites = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return str(self.user.username)


class Product_Pricing_Plan(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pricing_plan')
    plans = (
        ('FREE', 'Free Plan'),
        ('MONTHLY', 'Monthly Basic'),
        ('ANNUAL', 'Annual Pro'),
    )
    plan_type = models.CharField(max_length=25, choices=plans, default='FREE')
    price = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    feature = models.CharField(max_length=100, blank=True)


class Purchase(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product_plan = models.ForeignKey(Product_Pricing_Plan, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    available_until = models.DateTimeField(null=True, blank=True, default=None)

    def set_paid_until(self, date):
        self.available_until = date
        self.save()

    def has_paid_until(self, current_date=datetime.datetime.now()):
        # if this parameter is None, then pricing plan is free... for now
        if self.available_until is None:
            return True
        tmp=self.available_until.replace(tzinfo=None)
        return tmp > current_date




class Prod_Benefits(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=500)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)


class Reviews(models.Model):
    author = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[
            MaxValueValidator(5),
            MinValueValidator(0)
        ]
    )
    date = models.DateField(auto_now_add=True)
    body = models.CharField(max_length=50)
