# main/models.py
from django.db import models
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone

class Country(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="Страна")
    code = models.CharField(max_length=10, blank=True, default="", verbose_name="Код")  # RU, US
    phone_code = models.CharField(max_length=8, blank=True, default="", verbose_name="Телефонный код")  # +7, +40
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.phone_code})"

class City(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name="Страна",
    )
    name = models.CharField(max_length=150, verbose_name="Город")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=["country", "name"], name="uniq_city_per_country")
        ]

    def __str__(self):
        return f"{self.name} ({self.country.name})"

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    @property
    def can_sell(self):
        return self.is_staff or self.groups.filter(name="Издатели").exists()
    username = None
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=20, unique=True, blank=True, null=True)
    country = models.ForeignKey('Country', on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, verbose_name="Город", on_delete=models.SET_NULL, null=True, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    birth_year = models.IntegerField("Год рождения", null=True, blank=True)

    created_at = models.DateTimeField("Создан", auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # суперпользователь создаётся по email+password

    objects = CustomUserManager()

    def __str__(self):
        return self.email
class Profile(models.Model):
    GENDER_CHOICES = (
        ('male', 'Мужчина'),
        ('female', 'Женщина'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name='Пол'
    )

    bio = models.TextField(
        blank=True,
        verbose_name='О себе'
    )

    social_link = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Ссылка на соцсеть'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания профиля'
    )

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль: {self.user.first_name}'


@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance: CustomUser, created: bool, **kwargs):
    """Создаём профиль при создании пользователя"""
    if created:
        Profile.objects.create(user=instance)

class Category(models.Model):
    """
    Категории каталога (поддерживает древовидность через parent).
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    image = models.ImageField(upload_to='categories/', blank=True, verbose_name='Картинка')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Автор'
    )

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория'
    )

    brand = models.CharField(max_length=100, blank=True, verbose_name='Бренд')

    # Доп. характеристики (цвет, размер и т.д.)
    attributes = models.JSONField(default=dict, blank=True, verbose_name='Характеристики')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
        ]

    def __str__(self) -> str:
        return self.title


class ProductImage(models.Model):
    """
    Картинки товара. is_main — главная картинка.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='Товар')
    image = models.ImageField(upload_to='products/', verbose_name='Изображение')
    is_main = models.BooleanField(default=False, verbose_name='Главное')
    order = models.IntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return f"Image for {self.product.title}"

class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Товар",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        unique_together = [("user", "product")]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.product_id}"

class Review(models.Model):
    """
    Отзывы о товарах.
    """
    RATING_CHOICES = [
        (1, '1 - Ужасно'),
        (2, '2 - Плохо'),
        (3, '3 - Нормально'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='reviews',
        verbose_name='Автор',
        null=True,
        blank=True,
    )
    author_name_snapshot = models.CharField(max_length=150, verbose_name='Имя автора (снимок)')
    author_email_snapshot = models.EmailField(blank=True, verbose_name='Email автора (снимок)')

    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Оценка')
    title = models.CharField(max_length=200, blank=True, verbose_name='Заголовок')
    comment = models.TextField(verbose_name='Комментарий')

    is_approved = models.BooleanField(default=True, verbose_name='Одобрен')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ['product', 'author']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['author']),
        ]

    def save(self, *args, **kwargs):
        if self.author and not self.author_name_snapshot:
            self.author_name_snapshot = (
                    self.author.first_name
                    or self.author.email
                    or "Пользователь"
            )
        if self.author and not self.author_email_snapshot:
            self.author_email_snapshot = self.author.email or ""
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.author:
            who = (self.author.first_name or self.author.email or "Unknown")
        else:
            who = self.author_name_snapshot or "Unknown"
        return f"Отзыв на {self.product.title} от {who}"


class Chat(models.Model):
    """
    Чаты только техподдержка/консультант.
    """
    CHAT_TYPES = (
        ('support', 'Техподдержка'),
        ('consultant', 'Консультант'),
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_support_chats",
        help_text="Оператор"
    )

    STATUS_CHOICES = (
        ("open", "Открыт"),
        ("waiting", "Ожидание"),
        ("closed", "Закрыт"),
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")

    last_message_at = models.DateTimeField(null=True, blank=True)

    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES, verbose_name='Тип чата')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='chats', verbose_name='Пользователь')

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chats',
        verbose_name='Товар'
    )

    is_active = models.BooleanField(default=True, verbose_name='Активен')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        indexes = [
            models.Index(fields=['chat_type', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self) -> str:
        return f"Chat({self.chat_type}) #{self.pk}"

class Message(models.Model):
    """
    Сообщения чата.
    """
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    image = models.ImageField(upload_to="support_chat/%Y/%m/", blank=True, null=True)
    text = models.TextField(verbose_name='Текст')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['chat', 'created_at']),
            models.Index(fields=['sender']),
        ]

    def __str__(self) -> str:
        return f"Msg #{self.pk} in chat #{self.chat_id}"

@receiver(post_save, sender=Message)
def bump_chat_last_message(sender, instance: Message, created: bool, **kwargs):
    if not created:
        return
    Chat.objects.filter(pk=instance.chat_id).update(last_message_at=timezone.now())