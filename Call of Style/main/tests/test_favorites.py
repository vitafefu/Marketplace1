from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Category, Product, Favorite
from .utils import dummy_image

class FavoritesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(email="u@example.com", password="pass12345")
        cls.owner = CustomUser.objects.create_user(email="o@example.com", password="pass12345")
        cls.cat = Category.objects.create(name="Одежда", image=dummy_image("cat.jpg"), description="desc")
        cls.product = Product.objects.create(
            title="Tee",
            description="desc",
            brand="Brand",
            attributes={},
            category=cls.cat,
            owner=cls.owner,
        )

    def test_toggle_favorites_requires_auth(self):
        url = reverse("toggle_favorite", kwargs={"product_id": self.product.id})
        resp = self.client.post(url)
        self.assertIn(resp.status_code, (302, 401, 403))

    def test_toggle_favorites_add(self):
        self.client.force_login(self.user)
        url = reverse("toggle_favorite", kwargs={"product_id": self.product.id})
        resp = self.client.post(url)
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())

    def test_toggle_favorites_add_then_remove(self):
        self.client.force_login(self.user)
        url = reverse("toggle_favorite", kwargs={"product_id": self.product.id})

        self.client.post(url)
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())

        self.client.post(url)
        self.assertFalse(Favorite.objects.filter(user=self.user, product=self.product).exists())
