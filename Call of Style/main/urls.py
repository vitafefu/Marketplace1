from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import RegisterView


urlpatterns = [
    path('', views.home, name='home'),
    path('index/', views.index, name='index'),
    path('profile/avatar/', views.profile_avatar_upload, name='profile_avatar_upload'),
    path('profile/avatar/delete/', views.profile_avatar_delete, name='profile_avatar_delete'),
    path("api/reverse-geocode/", views.api_reverse_geocode, name="api_reverse_geocode"),
    path("api/location/", views.api_set_location, name="api_set_location"),
    path("api/location/suggest/", views.api_location_suggest, name="api_location_suggest"),
    path("api/location/set/", views.api_set_location, name="api_set_location"),
    path("api/location/set/guest/", views.api_set_location_guest, name="api_set_location_guest"),
    path("api/reverse-geocode/", views.api_reverse_geocode, name="api_reverse_geocode"),
    path('login/', views.login_view, name='login'),
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('register/', views.register_view, name='register'),
    path("api/countries/", views.countries_suggest, name="countries_suggest"),
    path("api/cities/", views.cities_suggest, name="cities_suggest"),
    path('profile/', views.profile_view, name='profile'),
    path('favorites/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('support/<str:chat_type>/', views.support_chat, name='support_chat'),
    path('support/<str:chat_type>/<int:product_id>/', views.support_chat, name='support_chat_product'),
    path('chat/<int:chat_id>/send/', views.send_message, name='send_message'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('add-product/', views.add_product, name='add_product'),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)