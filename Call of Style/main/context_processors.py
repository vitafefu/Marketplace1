from .models import Favorite

def favorites_context(request):
    if request.user.is_authenticated:
        ids = set(
            Favorite.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    else:
        ids = set()
    return {"favorite_ids": ids}
