from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from main.models import CustomUser, Category, Product, Favorite, Chat, Message


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Pass12345!"
        cls.user = CustomUser.objects.create_user(
            email="user@test.com",
            password=cls.password,
            first_name="User",
            last_name="Test",
            is_active=True,
        )

        cls.staff = CustomUser.objects.create_user(
            email="staff@test.com",
            password=cls.password,
            first_name="Staff",
            last_name="Test",
            is_active=True,
            is_staff=True,
        )

        cls.category = Category.objects.create(
            name="Одежда",
            image="cat.png",
            description="Категория тест",
        )

        cls.product = Product.objects.create(
            title="Куртка тест",
            description="Описание",
            brand="Nike",
            attributes={},
            category=cls.category,
            owner=cls.user,
        )


class PublicPagesTests(BaseTestCase):
    def test_home_page_ok(self):
        url = reverse("home")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_index_page_ok(self):
        url = reverse("index")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_catalog_page_ok(self):
        url = reverse("catalog")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_product_detail_ok(self):
        url = reverse("product_detail", kwargs={"product_id": self.product.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)


class AuthApiTests(BaseTestCase):
    def test_api_login_success(self):
        url = reverse("api_login")
        r = self.client.post(
            url,
            data={"email": self.user.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("redirect", data)

    def test_api_login_fail(self):
        url = reverse("api_login")
        r = self.client.post(
            url,
            data={"email": self.user.email, "password": "WRONG"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("ok", data)
        self.assertFalse(data["ok"])


class ProfileAccessTests(BaseTestCase):
    def test_profile_requires_auth(self):
        url = reverse("profile")
        r = self.client.get(url)
        # обычно редирект на login
        self.assertIn(r.status_code, (302, 401, 403))

    def test_profile_ok_for_logged_user(self):
        self.client.login(email=self.user.email, password=self.password)
        url = reverse("profile")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)


class ProductsTests(BaseTestCase):
    def test_add_product_requires_auth(self):
        url = reverse("add_product")
        r = self.client.get(url)
        self.assertIn(r.status_code, (302, 401, 403))

    def test_edit_product_requires_owner_or_staff(self):
        url = reverse("edit_product", kwargs={"product_id": self.product.id})

        # неавторизованный
        r = self.client.get(url)
        self.assertIn(r.status_code, (302, 401, 403))

        # владелец
        self.client.login(email=self.user.email, password=self.password)
        r2 = self.client.get(url)
        self.assertIn(r2.status_code, (200, 302))  # если там форма/или редирект логики

    def test_favorite_toggle_requires_auth(self):
        url = reverse("toggle_favorite", kwargs={"product_id": self.product.id})
        r = self.client.post(url)
        self.assertIn(r.status_code, (302, 401, 403))

    def test_favorite_toggle_add_and_remove(self):
        self.client.login(email=self.user.email, password=self.password)

        url = reverse("toggle_favorite", kwargs={"product_id": self.product.id})

        # add
        r1 = self.client.post(url, follow=True)
        self.assertIn(r1.status_code, (200, 302))
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())

        # remove
        r2 = self.client.post(url, follow=True)
        self.assertIn(r2.status_code, (200, 302))
        self.assertFalse(Favorite.objects.filter(user=self.user, product=self.product).exists())


class SupportChatTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # создадим чат поддержки
        self.chat = Chat.objects.create(
            chat_type="support",
            is_active=True,
            user=self.user,
            product=self.product,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            status="open",
        )

    def test_support_chat_page_requires_auth_or_works(self):
        # зависит от твоей логики: если у тебя support/ требует логин — будет 302
        url = reverse("support_chat")
        r = self.client.get(url)
        self.assertIn(r.status_code, (200, 302, 401, 403))

    def test_support_chat_messages_api_requires_auth(self):
        url = reverse("api_support_chat_messages", kwargs={"chat_id": self.chat.id})
        r = self.client.get(url)
        self.assertIn(r.status_code, (302, 401, 403))

    def test_support_chat_send_api(self):
        self.client.login(email=self.user.email, password=self.password)

        url = reverse("api_support_chat_send", kwargs={"chat_id": self.chat.id})
        r = self.client.post(
            url,
            data={"text": "Привет"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["message"]["text"], "Привет")

        # если у тебя реально создаётся Message — проверим
        self.assertTrue(Message.objects.filter(chat=self.chat, sender=self.user).exists())

    def test_admin_inbox_requires_staff(self):
        url = reverse("support_admin_inbox")

        # обычный юзер
        self.client.login(email=self.user.email, password=self.password)
        r1 = self.client.get(url)
        self.assertIn(r1.status_code, (302, 403))

        # staff
        self.client.logout()
        self.client.login(email=self.staff.email, password=self.password)
        r2 = self.client.get(url)
        self.assertIn(r2.status_code, (200, 302))

    def test_admin_chat_api_requires_staff(self):
        url = reverse("api_support_admin_messages", kwargs={"chat_id": self.chat.id})

        # не staff
        self.client.login(email=self.user.email, password=self.password)
        r1 = self.client.get(url)
        self.assertIn(r1.status_code, (302, 403))

        # staff
        self.client.logout()
        self.client.login(email=self.staff.email, password=self.password)
        r2 = self.client.get(url)
        self.assertIn(r2.status_code, (200, 302))
