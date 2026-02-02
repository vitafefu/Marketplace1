from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Category, Product, ProductImage
from .utils import dummy_image

class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(email="owner@example.com", password="pass12345")
        cls.cat = Category.objects.create(name="Одежда", image=dummy_image("cat.jpg"), description="desc")

        cls.p1 = Product.objects.create(
            title="Nike Air",
            description="desc",
            brand="Nike",
            attributes={"size": "M"},
            category=cls.cat,
            owner=cls.user,
        )
        ProductImage.objects.create(product=cls.p1, image=dummy_image("p1_main.jpg"), is_main=True, order=0)

    def test_index_page_ok(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)

    def test_catalog_page_ok(self):
        resp = self.client.get(reverse("catalog"))
        self.assertEqual(resp.status_code, 200)

    def test_product_detail_ok(self):
        resp = self.client.get(reverse("product_detail", kwargs={"product_id": self.p1.id}))
        self.assertEqual(resp.status_code, 200)

    def test_product_images_ordering(self):
        ProductImage.objects.create(product=self.p1, image=dummy_image("y.jpg"), is_main=False, order=2)
        ProductImage.objects.create(product=self.p1, image=dummy_image("z.jpg"), is_main=False, order=1)

        qs = self.p1.images.all().order_by("order")
        self.assertEqual([img.order for img in qs], [0, 1, 2])
