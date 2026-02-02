import json
from django.test import TestCase
from django.urls import reverse
from main.models import CustomUser, Chat, Message

class SupportChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(email="u@example.com", password="pass12345")

    def test_open_support_chat_requires_auth(self):
        resp = self.client.get(reverse("support_chat"))
        self.assertIn(resp.status_code, (302, 401, 403))

    def test_send_message_api(self):
        self.client.force_login(self.user)

        chat = Chat.objects.create(
            chat_type="support",
            is_active=True,
            user=self.user,
            status="open",
        )

        url = reverse("api_support_chat_send", kwargs={"chat_id": chat.id})
        payload = {"text": "hello"}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")

        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(Message.objects.filter(chat=chat, text="hello").exists())
