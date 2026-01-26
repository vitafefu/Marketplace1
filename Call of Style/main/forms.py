from django import forms
from django.db import transaction
from .models import Review, CustomUser, Profile, Country, City
from datetime import date

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']

        widgets = {
            'rating': forms.RadioSelect,
            'title': forms.TextInput(attrs={
                'placeholder': 'Краткий заголовок (необязательно)',
            }),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Поделитесь вашим мнением о товаре',
            }),
        }
class ProfileUpdateForm(forms.Form):
    name = forms.CharField(required=True, max_length=150)
    email = forms.EmailField(required=True)

    country_id = forms.IntegerField(required=True)
    city_id = forms.IntegerField(required=True)

    phone = forms.CharField(required=True, max_length=20)
    birth_date = forms.DateField(required=True, input_formats=["%Y-%m-%d"])

    # Profile
    avatar = forms.ImageField(required=False)
    gender = forms.ChoiceField(required=True, choices=Profile.GENDER_CHOICES)
    social_link = forms.CharField(required=False, max_length=255)
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, user: CustomUser, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Имя должно быть минимум 2 символа")
        return name

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Этот email уже занят")
        return email

    def clean_birth_date(self):
        bd = self.cleaned_data.get("birth_date")
        if not bd:
            return bd  # поле необязательное

        today = date.today()

        # границы
        if bd > today or bd < date(1900, 1, 1):
            raise forms.ValidationError("Введите корректную дату рождения")

        # возраст >= 14
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        if age < 14:
            raise forms.ValidationError("Вам должно быть не менее 14 лет")

        return bd

    def clean(self):
        cleaned = super().clean()

        # страна/город только из подсказки
        country_id = cleaned.get("country_id")
        city_id = cleaned.get("city_id")

        try:
            country = Country.objects.get(id=int(country_id), is_active=True)
        except Exception:
            self.add_error("country_id", "Выберите страну из подсказки")
            return cleaned

        try:
            city = City.objects.get(id=int(city_id), is_active=True)
        except Exception:
            self.add_error("city_id", "Выберите город из подсказки")
            return cleaned

        if city.country_id != country.id:
            self.add_error("city_id", "Город не относится к выбранной стране")
            return cleaned

        cleaned["country_obj"] = country
        cleaned["city_obj"] = city

        # social link (по желанию — очень мягкая проверка)
        link = (cleaned.get("social_link") or "").strip()
        if link and not (link.startswith("http://") or link.startswith("https://")):
            self.add_error("social_link", "Ссылка должна начинаться с http:// или https://")

        return cleaned

    @transaction.atomic
    def save(self):
        u = self.user

        u.first_name = self.cleaned_data["name"]
        u.email = self.cleaned_data["email"]
        u.country = self.cleaned_data["country_obj"]
        u.city = self.cleaned_data["city_obj"]

        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone:
            digits = "".join(ch for ch in phone if ch.isdigit())
            phone_norm = "+" + digits if digits else ""
            if not phone_norm:
                raise forms.ValidationError("Введите корректный телефон")
            if CustomUser.objects.filter(phone=phone_norm).exclude(pk=u.pk).exists():
                raise forms.ValidationError("Этот номер телефона уже занят")
            u.phone = phone_norm

        bd = self.cleaned_data.get("birth_date")
        if bd:
            u.birth_date = bd
            u.birth_year = bd.year

        u.save()

        # профиль
        prof, _ = Profile.objects.get_or_create(user=u)

        new_avatar = self.cleaned_data.get("avatar")
        if new_avatar:
            prof.avatar = new_avatar

        prof.gender = self.cleaned_data.get("gender") or None
        prof.social_link = (self.cleaned_data.get("social_link") or "").strip()
        prof.bio = (self.cleaned_data.get("bio") or "").strip()
        prof.save()

        return u

