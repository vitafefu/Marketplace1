# main/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import *

# Кастомный заголовок
admin.site.site_header = "Call of Style Admin"
admin.site.site_title = "Call of Style"
admin.site.index_title = "🚀 Панель управления маркетплейсом"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'seller', 'status', 'created_at']
    list_filter = ['category', 'status', 'is_featured']
    search_fields = ['title', 'description']
    list_editable = ['price', 'status']

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'category', 'seller')
        }),
        ('Цены и количество', {
            'fields': ('price', 'old_price', 'quantity')
        }),
        ('Статус и характеристики', {
            'fields': ('status', 'attributes', 'is_featured')
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_method']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'balance']
    list_filter = ['user_type', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'product_count']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Товаров"


# Быстрая регистрация остальных моделей
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_main']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'author', 'rating', 'is_approved']
    list_editable = ['is_approved']


admin.site.register(Cart)
admin.site.register(CartItem)