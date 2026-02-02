import json
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.db import transaction
from django.db.utils import IntegrityError

from main.models import Country, City, CustomUser, Category, Product, Review, Chat, Message


class UrlMixin:
    """
    Подгони имена или пути под свой urls.py.
    Если у тебя есть name=..., лучше указывать name — reverse стабильнее.
    """
    URLS = {
        # location
        "location_suggest": None,           # name или None
        "set_location": None,
        "set_location_guest": None,
        "reverse_geocode": None,

        # search
        "search_suggest": None,

        # country/city suggest
        "countries_suggest": None,
        "cities_suggest": None,

        # auth
        "api_login": None,
        "api_register": None,               # name для RegisterView (например "api_register")

        # reviews
        "review_create": None,              # api_review_create
        "review_update": None,
        "review_delete": None,

        # support chat
        "support_chat_send": None,          # api_support_chat_send
        "support_chat_messages": None,      # api_support_chat_messages
    }

    PATHS = {
        # location
        "location_suggest": "/api/location/suggest/",
        "set_location": "/api/location/set/",
        "set_location_guest": "/api/location/guest/",
        "reverse_geocode": "/api/location/reverse/",

        # search
        "search_suggest": "/api/search/suggest/",

        # country/city suggest
        "countries_suggest": "/api/countries/suggest/",
        "cities_suggest": "/api/cities/suggest/",

        # auth
        "api_login": "/api/login/",
        "api_register": "/api/register/",

        # reviews
        "review_create": "/api/reviews/create/",
        "review_update": "/api/reviews/{id}/update/",
        "review_delete": "/api/reviews/{id}/delete/",

        # support chat
        "support_chat_send": "/api/support/chat/{chat_id}/send/",
        "support_chat_messages": "/api/support/chat/{chat_id}/messages/",
    }

    def u(self, key: str, **kwargs) -> str:
        """
        Достаёт URL: сначала reverse(name), если name задан,
        иначе берёт PATHS и форматирует.
        """
        name = self.URLS.get(key)
        if name:
            try:
                return reverse(name, kwargs=kwargs)
            except Exception:
                # если kwargs не нужны
                return reverse(name)
        path = self.PATHS[key]
        if kwargs:
            return path.format(**kwargs)
        return path


class BaseDataMixin:
    def make_geo(self):
        ru, _ = Country.objects.get_or_create(
            name="Russia",
            defaults={"phone_code": "+7", "is_active": True}
        )
        ro, _ = Country.objects.get_or_create(
            name="Romania",
            defaults={"phone_code": "+40", "is_active": True}
        )

        msk, _ = City.objects.get_or_create(
            country=ru,
            name="Moscow",
            defaults={"is_active": True}
        )
        buc, _ = City.objects.get_or_create(
            country=ro,
            name="Bucharest",
            defaults={"is_active": True}
        )

        return ru, ro, msk, buc

    def make_user(self, email="user@example.com", password="qwerty1", **extra):
        ru, ro, msk, buc = self.make_geo()
        return CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=extra.get("first_name", "User"),
            phone=extra.get("phone", "+79991112233"),
            country=extra.get("country", ru),
            city=extra.get("city", msk),
            birth_date=extra.get("birth_date", date(2000, 1, 1)),
            birth_year=2000,
        )

    def make_product(self, owner=None):
        if owner is None:
            owner = self.make_user(email="seller@example.com", phone="+79990001122")
        cat = Category.objects.create(name="Clothes")
        return Product.objects.create(
            owner=owner,
            title="T-Shirt",
            description="Nice",
            category=cat,
            brand="BrandX",
        )


class LocationApiTests(TestCase):
    def test_set_location_guest_requires_country(self):
        url = reverse("api_set_location_guest")
        r = self.client.post(
            url,
            data=json.dumps({"location": ""}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(r.json().get("ok", True))

    def test_set_location_guest_ok(self):
        url = reverse("api_set_location_guest")
        r = self.client.post(
            url,
            data=json.dumps({"location": "Moscow, Russia"}),
            content_type="application/json",
        )

        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("location"), "Moscow, Russia")

        # проверим, что записалось в session
        s = self.client.session
        self.assertEqual(s.get("country_name"), "Russia")
        self.assertEqual(s.get("city_name"), "Moscow")

        # и что оно реально появилось в БД
        self.assertTrue(Country.objects.filter(name="Russia").exists())
        self.assertTrue(City.objects.filter(name="Moscow", country__name="Russia").exists())

class SearchSuggestTests(UrlMixin, BaseDataMixin, TestCase):
    def test_search_suggest_short_query(self):
        r = self.client.get(self.u("search_suggest"), {"q": "a"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])

    def test_search_suggest_returns_category_and_product(self):
        owner = self.make_user(email="owner@example.com", phone="+79991112234")
        cat = Category.objects.create(name="Nike")
        Product.objects.create(
            owner=owner,
            title="Nike Air",
            description="Shoes",
            category=cat,
            brand="Nike",
        )
        r = self.client.get(self.u("search_suggest"), {"q": "Ni"})
        data = r.json()
        self.assertTrue(data["ok"])
        labels = [x["label"] for x in data["results"]]
        self.assertTrue(any("Nike" in s for s in labels))


class GeoSuggestTests(TestCase):
    def setUp(self):
        self.ru = Country.objects.create(name="Russia", phone_code="+7", is_active=True)
        self.ro = Country.objects.create(name="Romania", phone_code="+40", is_active=True)

        self.msk = City.objects.create(country=self.ru, name="Moscow", is_active=True)
        self.spb = City.objects.create(country=self.ru, name="Saint Petersburg", is_active=True)
        self.buc = City.objects.create(country=self.ro, name="Bucharest", is_active=True)

    def test_countries_suggest(self):
        url = reverse("countries_suggest")
        r = self.client.get(url, {"q": "Ru"})

        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertIn("results", data)
        self.assertTrue(any(x["name"] == "Russia" for x in data["results"]))

    def test_cities_suggest_filter_by_country(self):
        url = reverse("cities_suggest")
        r = self.client.get(url, {"q": "Mo", "country_id": str(self.ru.id)})

        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()["results"]

        # Moscow должна быть, Bucharest не должна
        names = [x["name"] for x in data]
        self.assertIn("Moscow", names)
        self.assertNotIn("Bucharest", names)
class AuthApiTests(UrlMixin, BaseDataMixin, TestCase):
    def test_api_login_success_json(self):
        u = self.make_user(email="login@example.com", password="qwerty1", phone="+79991112235")
        r = self.client.post(
            self.u("api_login"),
            data=json.dumps({"email": "login@example.com", "password": "qwerty1"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        self.assertIn("redirect", r.json())

    def test_api_login_wrong_password_returns_400_or_200(self):
        """
        У тебя сейчас при валидации возвращается 400.
        Если хочешь как в старых тестах (200), поменяй view.
        """
        u = self.make_user(email="login2@example.com", password="qwerty1", phone="+79991112236")
        r = self.client.post(
            self.u("api_login"),
            data=json.dumps({"email": "login2@example.com", "password": "wrongpw"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertIn(r.status_code, (200, 400))
        self.assertFalse(r.json().get("ok"))

    def test_api_login_short_password_validation(self):
        u = self.make_user(email="login3@example.com", password="qwerty1", phone="+79991112237")
        r = self.client.post(
            self.u("api_login"),
            data=json.dumps({"email": "login3@example.com", "password": "123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertIn(r.status_code, (200, 400))
        self.assertFalse(r.json().get("ok"))
        self.assertIn("errors", r.json())

    def test_register_success(self):
        ru, ro, msk, buc = self.make_geo()

        payload = {
            "email": "reg@gmail.com",
            "password": "qwerty1",
            "name": "Alex",
            "phone": "+7 (999) 111-22-33",
            "country_id": str(ru.id),
            "city_id": str(msk.id),
            "birth_date": "2000-01-01",
            "gender": "male",
        }
        r = self.client.post(
            self.u("api_register"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertIn(r.status_code, (200, 201))
        data = r.json()
        self.assertTrue(data.get("ok"), data)
        self.assertTrue(CustomUser.objects.filter(email="reg@gmail.com").exists())

    def test_register_duplicate_email(self):
        ru, ro, msk, buc = self.make_geo()
        CustomUser.objects.create_user(
            email="dup@gmail.com",
            password="qwerty1",
            first_name="Dup",
            phone="+79991112238",
            country=ru,
            city=msk,
            birth_date=date(2000, 1, 1),
            birth_year=2000,
        )

        payload = {
            "email": "dup@gmail.com",
            "password": "qwerty1",
            "name": "Alex",
            "phone": "+7 (999) 111-22-99",
            "country_id": str(ru.id),
            "city_id": str(msk.id),
            "birth_date": "2000-01-01",
            "gender": "male",
        }
        r = self.client.post(
            self.u("api_register"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertIn(r.status_code, (200, 400))
        self.assertFalse(r.json().get("ok"))
        self.assertIn("email", r.json().get("errors", {}))

    def test_register_city_not_in_country(self):
        ru, ro, msk, buc = self.make_geo()
        payload = {
            "email": "badgeo@gmail.com",
            "password": "qwerty1",
            "name": "Alex",
            "phone": "+7 (999) 111-22-11",
            "country_id": str(ru.id),
            "city_id": str(buc.id),  # город Румынии, страна РФ
            "birth_date": "2000-01-01",
            "gender": "male",
        }
        r = self.client.post(
            self.u("api_register"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertIn(r.status_code, (200, 400))
        self.assertFalse(r.json().get("ok"))
        self.assertIn("city", r.json().get("errors", {}))


class ReviewsApiTests(UrlMixin, BaseDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="rev@gmail.com", phone="+79991112239")
        self.product = self.make_product()

    def test_review_create_requires_auth(self):
        r = self.client.post(self.u("review_create"), data={"product_id": self.product.id, "rating": 5, "comment": "ok"})
        self.assertIn(r.status_code, (302, 401, 403))

    def test_review_create_success(self):
        self.client.force_login(self.user)
        r = self.client.post(
            self.u("review_create"),
            data={"product_id": self.product.id, "rating": 5, "title": "Cool", "comment": "Nice"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertTrue(Review.objects.filter(product=self.product, author=self.user).exists())

    def test_review_create_duplicate(self):
        self.client.force_login(self.user)
        Review.objects.create(
            product=self.product,
            author=self.user,
            author_name_snapshot="X",
            author_email_snapshot="x@x.com",
            rating=5,
            comment="a",
            title=""
        )
        r = self.client.post(
            self.u("review_create"),
            data={"product_id": self.product.id, "rating": 5, "title": "Cool", "comment": "Nice"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertIn(r.status_code, (200, 400))
        self.assertFalse(r.json().get("ok"))


class SupportChatApiTests(UrlMixin, BaseDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user(email="chatuser@gmail.com", phone="+79991112240")
        self.staff = CustomUser.objects.create_user(
            email="staff@gmail.com",
            password="qwerty1",
            first_name="Staff",
            phone="+79991112241",
        )
        self.staff.is_staff = True
        self.staff.save()

        self.chat = Chat.objects.create(chat_type="support", user=self.user, is_active=True, status="open")

    def test_support_chat_send_requires_auth(self):
        r = self.client.post(self.u("support_chat_send", chat_id=self.chat.id), data={"text": "hi"})
        self.assertIn(r.status_code, (302, 401, 403))

    def test_support_chat_send_ok(self):
        self.client.force_login(self.user)
        r = self.client.post(self.u("support_chat_send", chat_id=self.chat.id), data={"text": "hi"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        self.assertTrue(Message.objects.filter(chat=self.chat, sender=self.user, text="hi").exists())

    def test_support_chat_messages_after(self):
        Message.objects.create(chat=self.chat, sender=self.user, text="m1")
        Message.objects.create(chat=self.chat, sender=self.staff, text="m2")

        self.client.force_login(self.user)
        r = self.client.get(self.u("support_chat_messages", chat_id=self.chat.id), {"last_id": 0})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertTrue(len(data["messages"]) >= 2)
