# main/views.py
import json
import re
from datetime import datetime, date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q, Count
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils.http import url_has_allowed_host_and_scheme
import urllib.parse
import urllib.request
from django.db import transaction
from .forms import ReviewForm, ProfileUpdateForm

from .models import (
    CustomUser,
    Country,
    City,
    Profile,
    Product,
    ProductImage,
    Review,
    Category,
    Chat,
    Message,
    Favorite,
)
def _parse_location(text: str):
    raw = (text or "").strip()
    raw = " ".join(raw.split())
    if not raw:
        return "", ""
    if "," in raw:
        left, right = raw.split(",", 1)
        return left.strip(), right.strip()
    return "", raw  # без запятой считаем "страна"


@require_GET
def api_location_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"ok": True, "results": []})

    # 1) города
    cities = (
        City.objects
        .select_related("country")
        .filter(name__icontains=q)
        .order_by("name")[:10]
    )

    results = []
    for c in cities:
        results.append({
            "kind": "city",
            "label": f"{c.name}, {c.country.name}",
            "city": c.name,
            "country": c.country.name,
            "city_id": c.id,
            "country_id": c.country.id,
        })

    # 2) страны (если хочешь показывать отдельно)
    countries = (
        Country.objects
        .filter(name__icontains=q)
        .order_by("name")[:6]
    )

    for co in countries:
        results.append({
            "kind": "country",
            "label": co.name,
            "city": "",
            "country": co.name,
            "country_id": co.id,
            "city_id": "",
        })

    return JsonResponse({"ok": True, "results": results})
@require_POST
@login_required
def api_set_location(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "message": "Bad JSON"}, status=400)

    country_id = data.get("country_id")
    city_id = data.get("city_id")

    if not country_id or not city_id:
        return JsonResponse({"ok": False, "message": "country_id и city_id обязательны"}, status=400)

    try:
        country = Country.objects.get(id=country_id)
        city = City.objects.select_related("country").get(id=city_id, country_id=country_id)
    except (Country.DoesNotExist, City.DoesNotExist):
        return JsonResponse({"ok": False, "message": "Страна/город не найдены"}, status=404)

    user = request.user
    user.country = country
    user.city = city
    user.save(update_fields=["country", "city"])

    return JsonResponse({
        "ok": True,
        "location": f"{city.name}, {country.name}",
        "city": city.name,
        "country": country.name,
    })
@require_POST
@transaction.atomic
def api_set_location_guest(request):
    # ожидаем {location: "City, Country"} как у авторизованных
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    loc = (data.get("location") or "").strip()
    city_name, country_name = _parse_location(loc)

    if not country_name:
        return JsonResponse({"ok": False, "message": "Укажи страну (формат: Город, Страна)"}, status=400)

    country, _ = Country.objects.get_or_create(
        name=country_name,
        defaults={"is_active": True}
    )

    city = None
    if city_name:
        city, _ = City.objects.get_or_create(
            country=country,
            name=city_name,
            defaults={"is_active": True}
        )

    request.session["country_id"] = country.id
    request.session["country_name"] = country.name
    request.session["city_id"] = city.id if city else None
    request.session["city_name"] = city.name if city else ""

    pretty = f"{city.name}, {country.name}" if city else country.name
    return JsonResponse({"ok": True, "location": pretty})


@require_GET
def api_reverse_geocode(request):
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    if not lat or not lon:
        return JsonResponse({"ok": False, "error": "lat/lon required"}, status=400)

    params = urllib.parse.urlencode({
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 10,
        "addressdetails": 1,
    })
    url = f"https://nominatim.openstreetmap.org/reverse?{params}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "CallOfStyle/1.0 (local dev)",
        "Accept-Language": "ru",
    })

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    addr = data.get("address") or {}
    city = (
        addr.get("city") or addr.get("town") or addr.get("village")
        or addr.get("municipality") or addr.get("county") or ""
    )
    country = addr.get("country") or ""
    text = f"{city}, {country}" if city and country else (city or country or "")

    return JsonResponse({"ok": True, "location": text})
# =========================
# helpers
# =========================
def normalize_phone_any(phone_raw: str) -> str | None:
    """
    Делает +<digits>, например:
    "(40) 712-345-678" -> "+40712345678"
    "+7 (999) 111-22-33" -> "+79991112233"
    """
    if not phone_raw:
        return None
    digits = re.sub(r"\D", "", phone_raw)
    if not digits:
        return None
    return "+" + digits


def validate_phone_e164(phone: str) -> bool:
    # очень базово: + и 10..15 цифр
    return bool(re.fullmatch(r"\+\d{10,15}", phone))


def validate_phone_by_country_code(phone: str, phone_code: str | None) -> bool:
    if not validate_phone_e164(phone):
        return False
    if phone_code:
        phone_code = phone_code.strip()
        if phone_code and not phone.startswith(phone_code):
            return False
    return True

def can_add_products(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Издатели").exists()
    )

@require_GET
def api_search_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"ok": True, "results": []})

    q_lower = q.lower()

    results = []
    seen = set()

    def add(label: str, kind: str):
        label = (label or "").strip()
        if not label:
            return
        key = (kind, label.lower())
        if key in seen:
            return
        seen.add(key)
        results.append({"label": label})
        return len(results) >= 10

    # 1) Категории (если хочешь — удобно)
    # Можно убрать этот блок, если не надо.
    cats = (
        Category.objects
        .filter(name__icontains=q)
        .values_list("name", flat=True)[:10]
    )
    for name in cats:
        if add(name, "c"):
            return JsonResponse({"ok": True, "results": results})

    # 2) Товары: сначала title startswith, потом title contains
    # Берём побольше, потом уникализируем.
    p_qs = (
        Product.objects
        .filter(Q(title__icontains=q) | Q(brand__icontains=q))
        .values("title", "brand")
        [:60]
    )

    # небольшой “скоринг” прямо в python: startswith выше, чем contains
    def score_title(t: str) -> int:
        t = (t or "").strip().lower()
        if not t:
            return 999
        if t.startswith(q_lower):
            return 0
        if q_lower in t:
            return 1
        return 5

    def score_brand(b: str) -> int:
        b = (b or "").strip().lower()
        if not b:
            return 999
        if b.startswith(q_lower):
            return 2
        if q_lower in b:
            return 3
        return 6

    rows = list(p_qs)
    # сортируем, чтобы сначала шли лучшие совпадения по title
    rows.sort(key=lambda r: (score_title(r.get("title")), score_brand(r.get("brand"))))

    # 3) Добавляем title и brand
    for row in rows:
        title = row.get("title") or ""
        brand = row.get("brand") or ""

        # сначала название товара
        if add(title, "t"):
            break

        # потом бренд
        if brand and add(brand, "b"):
            break

    return JsonResponse({"ok": True, "results": results})

# =========================
# pages
# =========================
@require_POST
@login_required
def profile_avatar_upload(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)

    file = request.FILES.get("avatar")
    if not file:
        return JsonResponse({"ok": False, "message": "Файл не выбран"}, status=400)

    # если хочешь — можно ограничить размер:
    # if file.size > 5 * 1024 * 1024:
    #     return JsonResponse({"ok": False, "message": "Файл слишком большой (макс 5MB)"}, status=400)

    prof.avatar = file  # перезапишет предыдущий
    prof.save(update_fields=["avatar"])

    return JsonResponse({"ok": True, "avatar_url": prof.avatar.url})


@require_POST
@login_required
def profile_avatar_delete(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)

    if prof.avatar:
        prof.avatar.delete(save=False)   # удалит файл
        prof.avatar = None
        prof.save(update_fields=["avatar"])

    return JsonResponse({"ok": True})

@login_required
def profile_view(request):
    user = request.user

    if request.method == "POST" and request.POST.get("action") == "delete_avatar":
        prof = user.profile
        if prof.avatar:
            prof.avatar.delete(save=False)  # удаляет файл
            prof.avatar = None
            prof.save()
        messages.success(request, "Аватар удалён")
        return redirect("profile")

    user_reviews = Review.objects.filter(author=request.user).order_by('-created_at')[:20]

    favorite_products = (
        Product.objects
        .filter(favorited_by__user=request.user)
        .prefetch_related("images")
        .distinct()
        .order_by("-favorited_by__created_at")
    )

    if request.method == "POST" and request.POST.get("action") == "update_profile":
        form = ProfileUpdateForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён")
            return redirect("profile")
        messages.error(request, "Исправьте ошибки в форме")
    else:
        prof = getattr(request.user, "profile", None)
        form = ProfileUpdateForm(
            initial={
                "name": request.user.first_name or "",
                "email": request.user.email or "",
                "country_id": request.user.country_id or "",
                "city_id": request.user.city_id or "",
                "phone": request.user.phone or "",
                "birth_date": request.user.birth_date.isoformat() if request.user.birth_date else "",
                "gender": getattr(prof, "gender", "") if prof else "",
                "social_link": getattr(prof, "social_link", "") if prof else "",
                "bio": getattr(prof, "bio", "") if prof else "",
            },
            user=request.user
        )

    return render(request, "profile.html", {
        "user_reviews": user_reviews,
        "favorite_products": favorite_products,
        "profile_form": form,
    })


def home(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'home.html')


def index(request):
    products = Product.objects.all().order_by('-created_at')[:10]
    return render(request, 'index.html', {'products': products})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'login.html')

def register_view(request):
    """
    HTML страница регистрации.
    Регистрация делается через JS -> POST /api/register/
    """
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'register.html')


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    logout(request)
    return redirect('home')

@login_required
def favorites_view(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related("product")
        .order_by("-created_at")
    )
    products = [f.product for f in favorites]
    return render(request, "favorites.html", {"products": products})


@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    fav = Favorite.objects.filter(user=request.user, product=product).first()
    if fav:
        fav.delete()
        messages.info(request, "Убрано из избранного")
    else:
        Favorite.objects.create(user=request.user, product=product)
        messages.success(request, "Добавлено в избранное")

    # возвращаемся туда, откуда пришли (страница товара или каталог)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/profile/#favorites"
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/profile/#favorites"

    return redirect(next_url)

# =========================
# catalog
# =========================
def catalog_view(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', 'newest')

    products = Product.objects.all()

    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )

    if category_id:
        products = products.filter(category_id=category_id)
    elif sort_by == 'popular':
        products = products.annotate(
            reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
        ).order_by('-reviews_count', '-created_at')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'catalog.html', {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    images = product.images.all()

    reviews = product.reviews.filter(is_approved=True).select_related('author')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    is_owner_or_admin = (
            request.user.is_authenticated and (
            request.user.is_superuser or product.owner_id == request.user.id
    )
    )
    has_review = False
    user_review = None
    form = None

    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, author=request.user).first()
        has_review = user_review is not None

        # edit
        if request.method == 'POST' and request.POST.get('edit_review_id'):
            review = get_object_or_404(
                Review,
                id=request.POST.get('edit_review_id'),
                product=product,
                author=request.user
            )
            form = ReviewForm(request.POST, instance=review)
            if form.is_valid():
                form.save()
                messages.success(request, 'Отзыв обновлён')
                return redirect('product_detail', product_id=product.id)

        # create
        elif request.method == 'POST' and request.POST.get('action') == 'create' and not has_review:
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.product = product
                review.author = request.user
                review.is_approved = True
                review.save()
                messages.success(request, 'Спасибо за отзыв!')
                return redirect('product_detail', product_id=product.id)

        else:
            form = ReviewForm(initial={'rating': 5})
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()

    return render(request, 'product_detail.html', {
        'product': product,
        'images': images,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'form': form,
        'has_review': has_review,
        'user_review': user_review,
        'is_owner_or_admin': is_owner_or_admin,
        'is_favorite': is_favorite,
    })


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.author != request.user and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("Нет доступа")

    product_id = review.product.id
    review.delete()
    messages.success(request, 'Отзыв удалён')
    return redirect('product_detail', product_id=product_id)

def _review_stats(product):
    reviews = product.reviews.filter(is_approved=True)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    return round(avg_rating, 1), reviews.count()


def _review_payload(request, review, product):
    avg_rating, reviews_count = _review_stats(product)
    html = render_to_string(
        "main/_review_card.html",
        {"review": review, "user": request.user},
        request=request,
    )
    return {
        "ok": True,
        "review": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "comment": review.comment,
            "created_at": review.created_at.strftime("%d.%m.%Y"),
        },
        "html": html,
        "avg_rating": avg_rating,
        "reviews_count": reviews_count,
    }


def _form_errors(form):
    errors = {}
    for field, field_errors in form.errors.items():
        errors[field] = [str(err) for err in field_errors]
    return errors


@login_required
@require_POST
def api_review_create(request):
    product = get_object_or_404(Product, id=request.POST.get("product_id"))

    if Review.objects.filter(product=product, author=request.user).exists():
        return JsonResponse(
            {"ok": False, "errors": {"__all__": ["Вы уже оставили отзыв"]}},
            status=400,
        )

    form = ReviewForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": _form_errors(form)}, status=400)

    review = form.save(commit=False)
    review.product = product
    review.author = request.user
    review.is_approved = True
    review.save()

    return JsonResponse(_review_payload(request, review, product))


@login_required
@require_POST
def api_review_update(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    can_edit = review.author == request.user or request.user.is_staff or request.user.is_superuser

    if not can_edit:
        return JsonResponse(
            {"ok": False, "errors": {"__all__": ["Нет доступа"]}},
            status=403,
        )

    form = ReviewForm(request.POST, instance=review)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": _form_errors(form)}, status=400)

    form.save()

    return JsonResponse(_review_payload(request, review, review.product))


@login_required
@require_POST
def api_review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    product = review.product

    can_delete = review.author == request.user or request.user.is_staff or request.user.is_superuser

    if not can_delete:
        return JsonResponse(
            {"ok": False, "errors": {"__all__": ["Нет доступа"]}},
            status=403,
        )

    review.delete()
    avg_rating, reviews_count = _review_stats(product)
    return JsonResponse(
        {
            "ok": True,
            "review": {"id": review_id},
            "html": "",
            "avg_rating": avg_rating,
            "reviews_count": reviews_count,
        }
    )

# =========================
# chat
# =========================
@login_required
def support_chat(request, chat_type='support', product_id=None):
    product = None
    if product_id is not None:
        product = get_object_or_404(Product, id=product_id)

    chat, _created = Chat.objects.get_or_create(
        chat_type=chat_type,
        user=request.user,
        product=product,
        defaults={'is_active': True}
    )

    if request.method == 'POST':
        text = request.POST.get('message')
        if text:
            Message.objects.create(chat=chat, sender=request.user, text=text)
            if product_id is not None:
                return redirect('support_chat_product', chat_type=chat_type, product_id=product_id)
            return redirect('support_chat', chat_type=chat_type)

    return render(request, 'support_chat.html', {
        'chat': chat,
        'messages': chat.messages.all(),
        'chat_type': chat_type,
    })


@login_required
def send_message(request, chat_id):
    if request.method == 'POST':
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        text = request.POST.get('message')
        if text:
            Message.objects.create(chat=chat, sender=request.user, text=text)

    if chat.product_id:
        return redirect('support_chat_product', chat_type=chat.chat_type, product_id=chat.product_id)
    return redirect('support_chat', chat_type=chat.chat_type)


# =========================
# add product
# =========================
@login_required
def add_product(request):
    if not request.user.is_authenticated or not request.user.can_sell:
        return HttpResponseForbidden("Нет прав для добавления товаров")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        brand = request.POST.get('brand', '').strip()

        if not title or not description or not category_id:
            messages.error(request, "Заполните обязательные поля")
            return redirect('add_product')

        product = Product.objects.create(
            owner=request.user,
            title=title,
            description=description,
            category_id=category_id,
            brand=brand,
        )

        images = request.FILES.getlist('images')
        for i, image in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_main=(i == 0),
                order=i
            )

        messages.success(request, 'Товар добавлен')
        return redirect('product_detail', product_id=product.id)

    categories = Category.objects.all()
    return render(request, 'add_product.html', {'categories': categories})

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # доступ: владелец или суперюзер
    if not (request.user.is_superuser or request.user == product.owner):
        return HttpResponseForbidden("Нет доступа")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        brand = request.POST.get('brand', '').strip()

        if not title or not description or not category_id:
            messages.error(request, "Заполните обязательные поля")
            return redirect('edit_product', product_id=product.id)

        product.title = title
        product.description = description
        product.category_id = category_id
        product.brand = brand
        product.save()

        # если загрузили новые картинки — добавим
        images = request.FILES.getlist('images')
        if images:
            start_order = product.images.count()
            for i, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_main=False,
                    order=start_order + i
                )

        messages.success(request, "Товар обновлён")
        return redirect('product_detail', product_id=product.id)

    categories = Category.objects.all()
    return render(request, 'edit_product.html', {
        'product': product,
        'categories': categories,
    })
# =========================
# API: country suggestions
# =========================
@require_GET
def countries_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})

    qs = (
        Country.objects
        .filter(is_active=True, name__istartswith=q)
        .order_by("name")[:10]
    )

    return JsonResponse({
        "results": [
            {"id": c.id, "name": c.name, "phone_code": (c.phone_code or "")}
            for c in qs
        ]
    })

@require_GET
def cities_suggest(request):
    q = (request.GET.get("q") or "").strip()
    country_id = (request.GET.get("country_id") or "").strip()

    if not q:
        return JsonResponse({"results": []})

    qs = City.objects.filter(is_active=True)

    if country_id.isdigit():
        qs = qs.filter(country_id=int(country_id))

    qs = qs.filter(name__istartswith=q).order_by("name")[:10]

    return JsonResponse({
        "results": [{"id": c.id, "name": c.name} for c in qs]
    })

@require_POST
def api_login(request):
    wants_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
    )

    def respond(payload, status=200):
        if wants_json:
            return JsonResponse(payload, status=status)
        messages.error(request, payload.get('message') or 'Ошибка входа')
        return redirect('login')

    try:
        data = json.loads(request.body.decode('utf-8') or '{}') if (
            request.content_type and 'application/json' in request.content_type
        ) else request.POST
    except Exception:
        return respond({'ok': False, 'errors': {'__all__': ['Некорректный JSON']}}, status=400)

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    next_url = (data.get('next') or '').strip()

    errors = {}
    def add_error(field, msg): errors.setdefault(field, []).append(msg)

    if not email: add_error('email', 'Введите email')
    if not password: add_error('password', 'Введите пароль')

    email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    if email and (not email_pattern.match(email) or ' ' in email):
        add_error('email', 'Введите корректный email')
    if password and (' ' in password):
        add_error('password', 'Пароль не должен содержать пробелы')
    if password and len(password) < 6:
        add_error('password', 'Пароль минимум 6 символов')

    if errors:
        return respond({'ok': False, 'errors': errors}, status=400)

    user = authenticate(request, email=email, password=password)
    if not user:
        return respond({'ok': False, 'errors': {'__all__': ['Неверный email или пароль']}}, status=400)

    login(request, user)

    from django.conf import settings
    redirect_url = '/index/'
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host(), *getattr(settings, "ALLOWED_HOSTS", [])},
        require_https=request.is_secure(),
    ):
        redirect_url = next_url

    return respond({'ok': True, 'redirect': redirect_url})

# =========================
# API: register
# =========================
class RegisterView(View):
    def post(self, request):
        wants_json = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or 'application/json' in (request.headers.get('Accept') or '')
        )

        def respond(payload, status=200):
            if wants_json:
                return JsonResponse(payload, status=status)
            messages.error(request, payload.get('message') or 'Ошибка регистрации')
            return redirect('register')

        try:
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body.decode('utf-8') or '{}')
            else:
                data = request.POST
        except json.JSONDecodeError:
            return respond({'ok': False, 'errors': {'__all__': ['Некорректный JSON']}}, status=400)

        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        name = (data.get('name') or '').strip()
        phone_raw = (data.get('phone') or '').strip()
        country_id_raw = (data.get('country_id') or '').strip()
        city_id_raw = (data.get('city_id') or '').strip()
        birth_date_str = (data.get('birth_date') or '').strip()
        gender = (data.get('gender') or '').strip()

        allowed_domains = {
            'gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com',
            'icloud.com', 'me.com', 'mac.com', 'proton.me', 'protonmail.com',
            'aol.com', 'yandex.ru', 'ya.ru', 'mail.ru', 'list.ru',
            'bk.ru', 'inbox.ru', 'rambler.ru','dvfu.ru',
        }

        errors: dict[str, list[str]] = {}

        def add_error(field: str, message: str):
            errors.setdefault(field, []).append(message)

        # обязательные поля
        if not email:
            add_error('email', 'Введите email')
        if not password:
            add_error('password', 'Введите пароль')
        if not name:
            add_error('name', 'Введите имя')
        if not phone_raw:
            add_error('phone', 'Введите номер телефона')
        if not country_id_raw:
            add_error('country', 'Выберите страну из подсказки')
        if not city_id_raw:
            add_error('city', 'Выберите город из подсказки')
        if not birth_date_str:
            add_error('birth_date', 'Введите дату рождения')
        if not gender:
            add_error('gender', 'Выберите пол')

        # email
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        if email and not email_pattern.match(email):
            add_error('email', 'Введите корректный email адрес')
        if email:
            domain = email.split('@')[-1].lower()
            if domain not in allowed_domains:
                add_error('email', 'Разрешены только популярные почтовые домены')

        # пароль
        if password and len(password) < 6:
            add_error('password', 'Пароль должен быть минимум 6 символов')

        # имя
        text_pattern = re.compile(r'^[A-Za-zА-Яа-яЁё]+(?:[\s-][A-Za-zА-Яа-яЁё]+)*$')
        if name.startswith(' '):
            add_error('name', 'Не начинайте с пробела')
        if name and (len(name.strip()) < 2 or not text_pattern.match(name.strip())):
            add_error('name', 'Имя: только буквы, пробелы и дефисы (минимум 2 символа)')

        # дата рождения
        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                today = date.today()
                if birth_date > today or birth_date < date(1900, 1, 1):
                    add_error('birth_date', 'Введите корректную дату рождения')
                else:
                    age = today.year - birth_date.year - (
                        (today.month, today.day) < (birth_date.month, birth_date.day)
                    )
                    if age < 14:
                        add_error('birth_date', 'Вам должно быть не менее 14 лет')
            except (ValueError, TypeError):
                        add_error('birth_date', 'Введите корректную дату рождения')

        if gender and gender not in {'male', 'female'}:
            add_error('gender', 'Выберите пол')

        # early exit
        if errors:
            return respond({'ok': False, 'errors': errors}, status=400)
        # достаём страну/город по id
        try:
            country_id = int(country_id_raw)
            country_obj = Country.objects.get(id=country_id, is_active=True)
        except (ValueError, TypeError, Country.DoesNotExist):
            return respond({'ok': False, 'errors': {'country': ['Страна не найдена']}}, status=400)

        try:
            city_id = int(city_id_raw)
            city_obj = City.objects.get(id=city_id, is_active=True)
        except (ValueError, TypeError, City.DoesNotExist):
            return respond({'ok': False, 'errors': {'city': ['Город не найден']}}, status=400)

        # проверяем что город реально принадлежит стране
        if city_obj.country_id != country_obj.id:
            return respond({'ok': False, 'errors': {'city': ['Город не относится к выбранной стране']}}, status=400)

        # телефон
        phone = normalize_phone_any(phone_raw)
        if not phone:
            return respond({'ok': False, 'errors': {'phone': ['Введите корректный номер телефона']}}, status=400)

        if not validate_phone_by_country_code(phone, country_obj.phone_code):
            msg = (
                f'Телефон должен начинаться с {country_obj.phone_code}'
                if country_obj.phone_code else 'Введите корректный телефон'
            )
            return respond({'ok': False, 'errors': {'phone': [msg]}}, status=400)
        # уникальность
        if CustomUser.objects.filter(email__iexact=email).exists():
            return respond({'ok': False, 'errors': {'email': ['Пользователь с таким email уже существует']}}, status=400)
        if CustomUser.objects.filter(phone=phone).exists():
            return respond({'ok': False, 'errors': {'phone': ['Пользователь с таким номером телефона уже существует']}}, status=400)
        # создаём пользователя
        try:
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=name.strip(),
                phone=phone,
                country=country_obj,
                city=city_obj,
                birth_date=birth_date,
                birth_year=birth_date.year if birth_date else None,
            )
            prof, _ = Profile.objects.get_or_create(user=user)
            prof.gender = gender
            prof.save()
            login(request, user)

        except Exception as exc:
            return respond({'ok': False, 'errors': {'__all__': [f'Ошибка регистрации: {exc}']}}, status=500)

        return respond({
            'ok': True,
            'redirect': '/index/',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.first_name,
                'phone': user.phone,
                'country': country_obj.name,
                'city': city_obj.name,
                'birth_date': user.birth_date.isoformat() if user.birth_date else birth_date_str,
            }
        })