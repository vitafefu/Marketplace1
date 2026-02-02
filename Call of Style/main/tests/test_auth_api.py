import json
from django.test import TestCase
from main.models import CustomUser, Country, City

class AuthApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name="Russia", code="RU", is_active=True, phone_code="+7")
        cls.city = City.objects.create(name="Vladivostok", is_active=True, country=cls.country)

    def test_register_success(self):
        url = "/api/register/"
        payload = {
            "email": "user@gmail.com",
            "password": "password12345",
            "name": "Иван",
            "phone": "+79123456789",
            "country_id": str(self.country.id),
            "city_id": str(self.city.id),
            "birth_date": "2000-01-01",
            "gender": "male",
        }

        resp = self.client.post(url, data=json.dumps(payload, ensure_ascii=False), content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertTrue(CustomUser.objects.filter(email="user@gmail.com").exists())

    def test_register_duplicate_email(self):
        CustomUser.objects.create_user(email="user@gmail.com", password="pass12345")
        url = "/api/register/"
        payload = {"email": "user@gmail.com", "password": "password12345"}

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)

        data = resp.json()
        self.assertFalse(data.get("ok"))

    def test_login_success(self):
        CustomUser.objects.create_user(email="user@gmail.com", password="password12345")
        url = "/api/login/"
        payload = {"email": "user@gmail.com", "password": "password12345"}

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json().get("ok"))

    def test_login_wrong_password(self):
        CustomUser.objects.create_user(email="user@gmail.com", password="password12345")
        url = "/api/login/"
        payload = {"email": "user@gmail.com", "password": "wrongpw"}

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(resp.json().get("ok"))
