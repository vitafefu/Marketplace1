from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from main.models import (
    Country, City, CustomUser, Profile,
    Category, Product, ProductImage,
    Favorite, Review,
    Chat, Message,
)
class RegisterApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(
            name="Russia",
            code="RU",
            phone_code="+7",
            is_active=True,
        )
        cls.city = City.objects.create(
            name="Moscow",
            country=cls.country,
            is_active=True,
        )

    def test_register_success(self):
        payload = {
            "email": "user@gmail.com",
            "password": "password123",
            "name": "Иван",
            "phone": "+79991234567",
            "country_id": str(self.country.id),
            "city_id": str(self.city.id),
            "birth_date": "2000-01-01",
            "gender": "male",
        }

        resp = self.client.post(
            "/api/register/",
            payload,
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        self.assertTrue(data["ok"])

        # пользователь реально создан
        self.assertTrue(
            CustomUser.objects.filter(email="user@gmail.com").exists()
        )

        user = CustomUser.objects.get(email="user@gmail.com")
        self.assertEqual(user.country, self.country)
        self.assertEqual(user.city, self.city)
        self.assertEqual(user.birth_year, 2000)
        self.assertTrue(hasattr(user, "profile"))  # profile создаётся сигналом

    def test_register_duplicate_email(self):
        CustomUser.objects.create_user(
            email="user@gmail.com",
            password="password123",
            phone="+79990000000",
        )

        payload = {
            "email": "user@gmail.com",
            "password": "password123",
            "name": "Иван",
            "phone": "+79991234567",
            "country_id": str(self.country.id),
            "city_id": str(self.city.id),
            "birth_date": "2000-01-01",
            "gender": "male",
        }

        resp = self.client.post(
            "/api/register/",
            payload,
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(resp.status_code, 400)

        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("email", data["errors"])

def dummy_png(name="x.png"):
    # минимальный “псевдо-png” байтовый файл (для ImageField в тестах)
    return SimpleUploadedFile(
        name,
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20,
        content_type="image/png",
    )


class CountryCityModelTests(TestCase):
    def test_country_str(self):
        c = Country.objects.create(name="Russia", code="RU", phone_code="+7", is_active=True)
        self.assertIn("Russia", str(c))
        self.assertIn("+7", str(c))

    def test_city_unique_per_country(self):
        c1 = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        c2 = Country.objects.create(name="Romania", phone_code="+40", is_active=True)

        City.objects.create(country=c1, name="Moscow", is_active=True)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                City.objects.create(country=c1, name="Moscow", is_active=True)

        City.objects.create(country=c2, name="Moscow", is_active=True)

class UserProfileModelTests(TestCase):
    def test_profile_created_by_signal(self):
        u = CustomUser.objects.create_user(
            email="u@gmail.com",
            password="pass12345",
            phone="+79990000000",
        )
        # signal post_save должен создать профиль
        self.assertTrue(Profile.objects.filter(user=u).exists())
        self.assertEqual(u.profile.user_id, u.id)

    def test_can_sell_property(self):
        u = CustomUser.objects.create_user(email="x@gmail.com", password="pass12345")
        self.assertFalse(u.can_sell)

        staff = CustomUser.objects.create_user(email="s@gmail.com", password="pass12345", is_staff=True)
        self.assertTrue(staff.can_sell)


class ProductModelsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        cls.city = City.objects.create(country=cls.country, name="Moscow", is_active=True)
        cls.owner = CustomUser.objects.create_user(
            email="owner@gmail.com",
            password="pass12345",
            phone="+79991112233",
            country=cls.country,
            city=cls.city,
        )
        cls.cat = Category.objects.create(
            name="Одежда",
            description="Категория",
            image=dummy_png("cat.png"),
        )

    def test_product_and_images_ordering(self):
        p = Product.objects.create(
            owner=self.owner,
            title="Куртка",
            description="desc",
            category=self.cat,
            brand="Nike",
            attributes={"size": "M"},
        )

        ProductImage.objects.create(product=p, image=dummy_png("a.png"), is_main=True, order=0)
        ProductImage.objects.create(product=p, image=dummy_png("c.png"), is_main=False, order=2)
        ProductImage.objects.create(product=p, image=dummy_png("b.png"), is_main=False, order=1)

        orders = list(p.images.values_list("order", flat=True))
        self.assertEqual(orders, [0, 1, 2])


class FavoriteModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        cls.city = City.objects.create(country=cls.country, name="Moscow", is_active=True)

        cls.user = CustomUser.objects.create_user(email="u@gmail.com", password="pass12345", phone="+79990000001")
        cls.owner = CustomUser.objects.create_user(email="o@gmail.com", password="pass12345", phone="+79990000002")

        cls.cat = Category.objects.create(name="Одежда", description="d", image=dummy_png("cat.png"))
        cls.product = Product.objects.create(
            owner=cls.owner, title="Tee", description="desc", category=cls.cat, brand="Brand", attributes={}
        )

    def test_favorite_unique_constraint(self):
        Favorite.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, product=self.product)


class ReviewModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        cls.city = City.objects.create(country=cls.country, name="Moscow", is_active=True)

        cls.author = CustomUser.objects.create_user(
            email="a@gmail.com", password="pass12345", phone="+79990000011", first_name="Alex"
        )
        cls.owner = CustomUser.objects.create_user(
            email="o@gmail.com", password="pass12345", phone="+79990000012"
        )
        cls.cat = Category.objects.create(name="Одежда", description="d", image=dummy_png("cat.png"))
        cls.product = Product.objects.create(
            owner=cls.owner, title="Sneakers", description="desc", category=cls.cat, brand="Brand", attributes={}
        )

    def test_review_snapshot_autofill_on_save(self):
        # ВАЖНО: у модели author_name_snapshot обязательный (blank=False)
        # Поэтому передаём пустую строку, и save() должен заполнить из автора.
        r = Review.objects.create(
            product=self.product,
            author=self.author,
            author_name_snapshot="",
            author_email_snapshot="",
            rating=5,
            title="t",
            comment="c",
            is_approved=True,
        )
        r.refresh_from_db()
        self.assertEqual(r.author_name_snapshot, "Alex")          # first_name
        self.assertEqual(r.author_email_snapshot, "a@gmail.com")  # email

    def test_review_unique_product_author(self):
        Review.objects.create(
            product=self.product,
            author=self.author,
            author_name_snapshot="",
            author_email_snapshot="",
            rating=5,
            title="t",
            comment="c",
            is_approved=True,
        )
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                product=self.product,
                author=self.author,
                author_name_snapshot="",
                author_email_snapshot="",
                rating=4,
                title="t2",
                comment="c2",
                is_approved=True,
            )


class ChatMessageModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(email="u@gmail.com", password="pass12345", phone="+79990000111")
        cls.staff = CustomUser.objects.create_user(email="s@gmail.com", password="pass12345", phone="+79990000112", is_staff=True)

        cls.country = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        cls.city = City.objects.create(country=cls.country, name="Moscow", is_active=True)
        cls.owner = CustomUser.objects.create_user(email="o@gmail.com", password="pass12345", phone="+79990000113")

        cls.cat = Category.objects.create(name="Одежда", description="d", image=dummy_png("cat.png"))
        cls.product = Product.objects.create(owner=cls.owner, title="Item", description="d", category=cls.cat)

    def test_message_signal_bumps_last_message_at(self):
        chat = Chat.objects.create(chat_type="support", user=self.user, product=self.product, is_active=True)

        self.assertIsNone(chat.last_message_at)

        Message.objects.create(chat=chat, sender=self.user, text="hello")
        chat.refresh_from_db()
        self.assertIsNotNone(chat.last_message_at)

        # проверим что время “свежее”
        self.assertLess(timezone.now() - chat.last_message_at, timedelta(seconds=5))
