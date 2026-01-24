# main/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.auth.models import Group
admin.site.unregister(Group)


from .models import (
    CustomUser,
    Country,
    City,
    Profile,
    Category,
    Product,
    ProductImage,
    Review,
    Favorite,
)

admin.site.site_header = "Call of Style — Админка"
admin.site.site_title = "Call of Style"
admin.site.index_title = "Управление каталогом"

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "phone_code", "is_active")
    # def has_module_permission(self, request):
    #     return False
# =========================
# City (нужно для autocomplete_fields у CustomUser.city)
# =========================
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    ordering = ("name",)

    # def get_model_perms(self, request):
    #     return {}
    #
    # def has_module_permission(self, request):
    #     return False

# =========================
# FORM: change user + profile fields
# =========================
class CustomUserChangeAdminForm(UserChangeForm):
    # Profile fields
    avatar = forms.ImageField(label="Аватар", required=False)
    gender = forms.ChoiceField(label="Пол", choices=Profile.GENDER_CHOICES, required=False)
    social_link = forms.CharField(label="Ссылка на соцсеть", required=False, max_length=255)
    bio = forms.CharField(label="О себе", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = CustomUser
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            prof, _ = Profile.objects.get_or_create(user=self.instance)
            self.fields["avatar"].initial = getattr(prof, "avatar", None)
            self.fields["gender"].initial = getattr(prof, "gender", None) or ""
            self.fields["social_link"].initial = getattr(prof, "social_link", "")
            self.fields["bio"].initial = getattr(prof, "bio", "")


# =========================
# FORM: create user (admin)
# =========================
class CustomUserCreateAdminForm(UserCreationForm):
    # Profile fields
    avatar = forms.ImageField(label="Аватар", required=False)
    gender = forms.ChoiceField(label="Пол", choices=Profile.GENDER_CHOICES, required=False)
    social_link = forms.CharField(label="Ссылка на соцсеть", required=False, max_length=255)
    bio = forms.CharField(label="О себе", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "email",
            "phone",
            "city",
            "birth_date",
            "password1",
            "password2",
        )


# =========================
# ADMIN: CustomUser
# =========================
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    actions = None

    form = CustomUserChangeAdminForm
    add_form = CustomUserCreateAdminForm

    list_display = (
        "avatar_preview",
        "display_name",
        "phone",
        "display_city",
        "display_birth_date",
        "display_gender",
        "email",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_display_links = ("avatar_preview", "display_name")

    search_fields = ("first_name", "email", "phone", "city__name")
    list_filter = ("is_staff", "is_active", "city", "profile__gender")
    ordering = ("-date_joined",)

    autocomplete_fields = ("city",)

    # поля при создании
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                # аккаунт
                "first_name",
                "email",
                "phone",
                "city",
                "birth_date",
                "password1",
                "password2",

                # профиль
                "avatar",
                "gender",
                "social_link",
                "bio",

                # права
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
    )

    # редактирование
    fieldsets = (
        ("Личные данные", {"fields": ("first_name", "phone", "city", "birth_date","email")}),
        ("Профиль", {"fields": ("avatar", "gender", "social_link", "bio")}),
        ("Права доступа", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Даты", {"fields": ("last_login", "date_joined", "created_at")}),
    )

    readonly_fields = ("last_login", "date_joined", "created_at")

    def display_name(self, obj):
        return obj.first_name.strip() if obj.first_name else "—"
    display_name.short_description = "Имя"

    def display_city(self, obj):
        return obj.city.name if getattr(obj, "city", None) else "—"
    display_city.short_description = "Город"

    def display_birth_date(self, obj):
        return obj.birth_date.strftime("%Y-%m-%d") if getattr(obj, "birth_date", None) else "—"
    display_birth_date.short_description = "Дата рождения"

    def display_gender(self, obj):
        prof = getattr(obj, "profile", None)
        if not prof or not getattr(prof, "gender", None):
            return "—"
        return dict(Profile.GENDER_CHOICES).get(prof.gender, prof.gender)
    display_gender.short_description = "Пол"

    def avatar_preview(self, obj):
        prof = getattr(obj, "profile", None)
        if prof and getattr(prof, "avatar", None):
            url = prof.avatar.url
            change_url = reverse("admin:main_customuser_change", args=[obj.pk])
            return format_html(
                '<a href="{}"><img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" /></a>',
                change_url, url
            )
        return "—"
    avatar_preview.short_description = "Аватар"

    def save_model(self, request, obj, form, change):
        # сохраняем CustomUser (включая city/birth_date/phone/email/first_name)
        super().save_model(request, obj, form, change)

        # синхронизируем Profile из формы
        prof, _ = Profile.objects.get_or_create(user=obj)

        new_avatar = form.cleaned_data.get("avatar")
        if new_avatar:
            prof.avatar = new_avatar

        prof.gender = form.cleaned_data.get("gender") or None
        prof.social_link = form.cleaned_data.get("social_link", "")
        prof.bio = form.cleaned_data.get("bio", "")
        prof.save()


# =========================
# Category
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "products_count")
    search_fields = ("name",)

    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "Товаров"


# =========================
# Product
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "owner", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description", "brand", "owner__email", "owner__first_name")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # staff/издатель видит только свои
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

# =========================
# ProductImage
# =========================
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_main", "order")
    list_filter = ("is_main",)
    ordering = ("product", "order")


# =========================
# Review
# =========================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__title", "author__email", "author__first_name", "comment")

# =========================
# Favorite (Избранное)
# =========================
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user__first_name", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__email",
        "user__first_name",
        "product__title",
        "product__brand",
    )
    autocomplete_fields = ("user", "product")
    ordering = ("-created_at",)

