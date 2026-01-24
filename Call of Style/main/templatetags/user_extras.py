# main/templatetags/user_extras.py
from django import template

register = template.Library()

@register.filter
def display_name(user, max_len=10):
    """
    Берём first_name если есть, иначе email.
    Обрезаем до первого пробела.
    Если длина > max_len -> режем и добавляем ...
    """
    try:
        max_len = int(max_len)
    except Exception:
        max_len = 10

    if not user:
        return ""

    raw = (getattr(user, "first_name", "") or "").strip()
    if not raw:
        raw = (getattr(user, "email", "") or "").strip()

    if not raw:
        return ""

    s = raw.split(" ")[0]  # до пробела

    if len(s) > max_len:
        return s[:max_len] + "..."

    return s
