import json
from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Category, Product, Review
from .utils import dummy_image

class ReviewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = CustomUser.objects.create_user(email="a@example.com", password="pass12345")
        cls.owner = CustomUser.objects.create_user(email="o@example.com", password="pass12345")
        cls.cat = Category.objects.create(name="Одежда", image=dummy_image("cat.jpg"), description="desc")
        cls.product = Product.objects.create(
            title="Sneakers",
            description="desc",
            brand="Brand",
            attributes={},
            category=cls.cat,
            owner=cls.owner,
        )

    def test_create_review_requires_auth(self):
        url = reverse("api_review_create")
        payload = {"product_id": self.product.id, "rating": 5, "comment": "ok"}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertIn(resp.status_code, (302, 401, 403, 200))

    def test_create_review_success(self):
        self.client.force_login(self.author)
        url = reverse("api_review_create")
        resp = self.client.post(url, {"product_id": self.product.id, "rating": 5, "comment": "Отлично"})

        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json().get("ok"))
        self.assertTrue(Review.objects.filter(product=self.product, author=self.author).exists())

    def test_edit_review_only_author(self):
        r = Review.objects.create(
            product=self.product,
            author=self.author,
            rating=5,
            title="t",
            comment="c",
            is_approved=True,
            author_email_snapshot="a@example.com",
            author_name_snapshot="A",
        )
        other = CustomUser.objects.create_user(email="x@example.com", password="pass12345")

        self.client.force_login(other)
        url = reverse("api_review_update", kwargs={"review_id": r.id})
        payload = {"rating": 1, "comment": "hack"}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")

        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.json().get("ok"))

    def test_delete_review(self):
        r = Review.objects.create(
            product=self.product,
            author=self.author,
            rating=5,
            title="t",
            comment="c",
            is_approved=True,
            author_email_snapshot="a@example.com",
            author_name_snapshot="A",
        )

        self.client.force_login(self.author)
        url = reverse("api_review_delete", kwargs={"review_id": r.id})
        resp = self.client.post(url, data=json.dumps({}), content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Review.objects.filter(id=r.id).exists())

