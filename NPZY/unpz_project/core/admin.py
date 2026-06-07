from django.contrib import admin
from .models import (
    Finance, RawMaterial, RawStorage, Product, ProductStorage,
    Employee, Purchase, Production, ProductionResult, Sale, Order, OrderItem, SalaryPayment
)

# ==========================================================
# 🏢 НАСТРОЙКА БИРЖИ ТЕНДЕРОВ И ДИНАМИЧЕСКИХ ПОЗИЦИЙ
# ==========================================================

class OrderItemInline(admin.TabularInline):
    """Позволяет добавлять от 1 до бесконечности товаров в один тендер на одном экране"""
    model = OrderItem
    extra = 1  # Количество пустых строк, доступных для заполнения по умолчанию
    min_num = 1  # Минимальное количество позиций в тендере


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'reward_price', 'status', 'deadline', 'get_total_volume')
    list_filter = ('status', 'deadline')
    search_fields = ('customer_name',)
    inlines = [OrderItemInline]  # Подключаем строки товаров внутрь карточки тендера

    def get_total_volume(self, obj):
        return f"{obj.total_quantity:.1f} т."
    get_total_volume.short_description = "Общий объем заказа"


# ==========================================================
# 📊 ПРОДВИНУТЫЙ МОНИТОРИНГ ОСТАЛЬНЫХ МОДЕЛЕЙ ЗАВОДА
# ==========================================================

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'fio', 'role', 'salary', 'status')
    list_filter = ('role', 'status')
    search_fields = ('fio',)


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'oil_type', 'price_per_ton', 'density', 'sulfur')
    list_filter = ('oil_type',)


@admin.register(RawStorage)
class RawStorageAdmin(admin.ModelAdmin):
    list_display = ('oil_material', 'current_volume', 'capacity')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_retail', 'price_wholesale', 'production_cost', 'type')
    list_filter = ('type',)
    search_fields = ('name',)


@admin.register(ProductStorage)
class ProductStorageAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'capacity')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'total_price', 'sale_type', 'client', 'date')
    list_filter = ('sale_type', 'product', 'date')
    search_fields = ('client',)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'oil', 'volume', 'total_price', 'supplier', 'date')
    list_filter = ('oil', 'date')


@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ('id', 'oil', 'volume_used', 'mode', 'additives', 'date')
    list_filter = ('mode', 'date')


# ==========================================================
# 🛠️ ПРОСТАЯ РЕГИСТРАЦИЯ ДЛЯ ОСТАВШИХСЯ СЛУЖЕБНЫХ ТАБЛИЦ
# ==========================================================

admin.site.register(Finance)
admin.site.register(ProductionResult)
admin.site.register(SalaryPayment)