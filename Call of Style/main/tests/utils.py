# main/tests/utils.py
import json
from django.core.files.uploadedfile import SimpleUploadedFile

def dummy_image(name="test.jpg"):
    return SimpleUploadedFile(
        name=name,
        content=b"\xff\xd8\xff\xe0" + b"0" * 100 + b"\xff\xd9",
        content_type="image/jpeg",
    )

def json_dumps(data):
    return json.dumps(data, ensure_ascii=False)
