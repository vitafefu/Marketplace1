from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import AbstractUser
# УБРАТЬ: from django.contrib.postgres.fields import JSONField
from django.dispatch import receiver
from django.db.models.signals import post_save

class User(AbstractUser):
    USER_TYPES = (
        ('buyer', 'Покупатель'),
        ('seller', 'Продавец'),
        ('admin', 'Администраator'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='buyer')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # ДОБАВИТЬ эти строки для решения конфликта:
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='main_user_set',  # ДОБАВИТЬ related_name
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='main_user_set',  # ДОБАВИТЬ related_name
        related_query_name='user',
    )

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

# Категории товаров
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


# Товары
class Product(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('active', 'Активный'),
        ('inactive', 'Неактивный'),
        ('sold', 'Продан'),

    )

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')

    # Основные характеристики
    brand = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=50, unique=True)  # Артикул
    quantity = models.IntegerField(default=1)  # Количество на складе

    # Дополнительные характеристики в JSON
    attributes = models.JSONField(default=dict, blank=True) # {color: 'red', size: 'XL'}

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)

    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['seller', 'status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.price} руб."


# Изображения товаров
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_main = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']


# Заказы
class Order(models.Model):
    ORDER_STATUS = (
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возврат'),
    )

    PAYMENT_METHODS = (
        ('card', 'Карта'),
        ('cash', 'Наличные'),
        ('online', 'Онлайн'),
    )

    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card')

    # Суммы
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Адрес доставки
    shipping_address = models.JSONField(default=dict)  # {city: 'Moscow', street: 'Lenina 1'}

    # Контакты
    customer_notes = models.TextField(blank=True)

    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} - {self.buyer.username}"


# Элементы заказа
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена на момент заказа

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"


# Отзывы и рейтинги
class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 - Ужасно'),
        (2, '2 - Плохо'),
        (3, '3 - Нормально'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'author']  # Один отзыв на товар от пользователя
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв на {self.product.title} от {self.author.username}"


# Корзина покупок
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Корзина {self.user.username}"


# Элементы корзины
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f'Профиль {self.user.username}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()