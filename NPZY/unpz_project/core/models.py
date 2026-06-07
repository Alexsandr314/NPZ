from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==========================================================
# 10. ФИНАНСЫ
# ==========================================================
class Finance(models.Model):
    balance = models.FloatField(default=1000000.0, verbose_name="Баланс предприятия (USD)")
    income = models.FloatField(default=0.0, verbose_name="Общий доход (USD)")
    expenses = models.FloatField(default=0.0, verbose_name="Общий расход (USD)")

    def __str__(self):
        return f"Баланс: {self.balance} USD"

    class Meta:
        verbose_name = "Финансы"
        verbose_name_plural = "Финансы"


# ==========================================================
# 2. НЕФТЬ (Сырье)
# ==========================================================
class RawMaterial(models.Model):
    OIL_TYPES = [
        ('light', 'Легкая (малосернистая)'),
        ('medium', 'Средняя'),
        ('heavy', 'Тяжелая (высокосернистая)'),
    ]

    name = models.CharField(max_length=100, verbose_name="Сорт нефти")
    oil_type = models.CharField(max_length=20, choices=OIL_TYPES, default='medium', verbose_name="Тип нефти")

    density = models.FloatField(verbose_name="Плотность (кг/м3)")
    sulfur = models.FloatField(verbose_name="Содержание серы (%)")
    water_content = models.FloatField(default=0.1, verbose_name="Содержание воды (%)")
    paraffin = models.FloatField(default=1.0, verbose_name="Парафины (%)")

    price_per_ton = models.FloatField(verbose_name="Цена за тонну (USD)")

    def __str__(self):
        return f"{self.name} ({self.get_oil_type_display()})"

    class Meta:
        verbose_name = "Сорт нефти"
        verbose_name_plural = "Сорта нефти"


# ==========================================================
# 3. СКЛАД СЫРЬЯ
# ==========================================================
class RawStorage(models.Model):
    oil_material = models.OneToOneField(RawMaterial, on_delete=models.CASCADE, verbose_name="Тип нефти")
    capacity = models.FloatField(verbose_name="Макс. объем (т)")
    current_volume = models.FloatField(default=0, verbose_name="Текущий объем (т)")

    def __str__(self):
        return f"Склад: {self.oil_material.name} ({self.current_volume}/{self.capacity})"

    class Meta:
        verbose_name = "Склад сырья"
        verbose_name_plural = "Склады сырья"


# ==========================================================
# 4. ПРОДУКЦИЯ
# ==========================================================
class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название продукта")
    price_retail = models.FloatField(default=0.0, verbose_name="Розница (USD за т)")
    price_wholesale = models.FloatField(default=0.0, verbose_name="Опт (USD за т)")

    # Оставляем поле для ручной корректировки, но добавим умный дефолт/метод
    production_cost = models.FloatField(default=0.0, verbose_name="Себестоимость (USD за т)")
    type = models.CharField(max_length=50, verbose_name="Тип продукта")

    def __str__(self):
        return f"{self.name} (${self.price_retail})"

    def calculate_real_cost(self):
        """
        Умный расчет себестоимости:
        Бензин и дизель требуют дорогих присадок и глубокой переработки.
        Мазут и асфальт — это остаточные продукты, их себестоимость ниже.
        """
        # Ищем последнюю операцию производства, чтобы узнать цену сырья
        latest_production = Production.objects.order_by('-date').first()
        if latest_production:
            base_oil_price = latest_production.oil.price_per_ton
        else:
            base_oil_price = 500.0  # Базовое значение, если производства еще не было

        name_lower = self.name.lower()
        if 'бензин' in name_lower:
            return base_oil_price * 1.3 + 50.0  # Сырье + работа установки + присадки
        elif 'дизель' in name_lower or 'керосин' in name_lower:
            return base_oil_price * 1.15 + 30.0  # Чуть дешевле бензина
        elif 'мазут' in name_lower or 'асфальт' in name_lower:
            return base_oil_price * 0.7  # Побочный продукт, стоит дешевле чистой нефти

        return base_oil_price  # Дефолт
# ==========================================================
# 5. СКЛАД ПРОДУКЦИИ
# ==========================================================
class ProductStorage(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    quantity = models.FloatField(default=0, verbose_name="Количество (т)")
    capacity = models.FloatField(default=5000.0, verbose_name="Вместимость (т)")

    def __str__(self):
        return f"Склад продукции: {self.product.name}"

    class Meta:
        verbose_name = "Склад продукции"
        verbose_name_plural = "Склады продукции"


# ==========================================================
# 1. РАБОТНИК
# ==========================================================
class Employee(models.Model):
    ROLE_CHOICES = [
        ('purchaser', 'Менеджер по закупкам'),
        ('technologist', 'Технолог'),
        ('sales', 'Менеджер по продажам'),
        ('accountant', 'Бухгалтер'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Аккаунт")
    fio = models.CharField(max_length=255, verbose_name="ФИО")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Должность")
    salary = models.FloatField(verbose_name="Оклад (USD)")
    status = models.CharField(max_length=50, default="Работает", verbose_name="Статус")

    def __str__(self):
        return f"{self.fio} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


# ==========================================================
# 6. ЗАКУПКА
# ==========================================================
class Purchase(models.Model):
    oil = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, verbose_name="Сорт нефти")
    volume = models.FloatField(verbose_name="Объем (т)")
    total_price = models.FloatField(verbose_name="Итоговая сумма (USD)")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата закупки")
    supplier = models.CharField(max_length=100, verbose_name="Поставщик")

    class Meta:
        verbose_name = "Закупка"
        verbose_name_plural = "Закупки"


# ==========================================================
# 7. ПРОИЗВОДСТВО
# ==========================================================
class Production(models.Model):
    MODE_CHOICES = [
        ('gasoline', 'Упор на бензин'),
        ('diesel', 'Упор на дизель'),
        ('heavy', 'Упор на мазут/асфальт'),
        ('balanced', 'Сбалансированный'),
    ]

    oil = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, verbose_name="Используемое сырье")
    volume_used = models.FloatField(verbose_name="Объем сырья (т)")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, verbose_name="Режим производства")
    additives = models.FloatField(default=0, verbose_name="Присадки (т)")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Партия №{self.id} - {self.mode}"

    class Meta:
        verbose_name = "Операция производства"
        verbose_name_plural = "Операции производства"


# ==========================================================
# 8. РЕЗУЛЬТАТ ПРОИЗВОДСТВА
# ==========================================================
class ProductionResult(models.Model):
    production = models.OneToOneField(Production, on_delete=models.CASCADE, related_name="result")
    gasoline = models.FloatField(default=0, verbose_name="Бензин (т)")
    diesel = models.FloatField(default=0, verbose_name="Дизель (т)")
    kerosene = models.FloatField(default=0, verbose_name="Керосин (т)")
    mazut = models.FloatField(default=0, verbose_name="Мазут (т)")
    asphalt = models.FloatField(default=0, verbose_name="Асфальт (т)")
    losses = models.FloatField(default=0, verbose_name="Потери (т)")

    class Meta:
        verbose_name = "Результат переработки"
        verbose_name_plural = "Результаты переработки"


# ==========================================================
# 9. ПРОДАЖА
# ==========================================================
class Sale(models.Model):
    SALE_TYPES = [('retail', 'Розница'), ('wholesale', 'Опт')]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField(verbose_name="Количество (т)")
    sale_type = models.CharField(max_length=10, choices=SALE_TYPES, default='retail')

    tax_rate = models.FloatField(default=12.0, verbose_name="НДС (%)")
    total_price = models.FloatField(verbose_name="Сумма сделки с налогом (USD)")

    client = models.CharField(max_length=255, verbose_name="Покупатель")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"


# ==========================================================
# 🛡️ БИРЖА ТЕНДЕРОВ И ЕЁ СОСТАВЛЯЮЩИЕ
# ==========================================================
class Order(models.Model):
    STATUS_CHOICES = [
        ('open', 'Открыт (Тендер)'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Завершен'),
        ('failed', 'Провален'),
    ]

    customer_name = models.CharField(max_length=200, verbose_name="Заказчик (например, Газпром нефть)")
    reward_price = models.FloatField(verbose_name="Цена контракта ($)")
    deadline = models.DateTimeField(verbose_name="Срок выполнения")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name="Статус")

    def __str__(self):
        return f"Тендер №{self.id} — {self.customer_name} (${self.reward_price})"

    @property
    def total_quantity(self):
        """Автоматически считает суммарный объем всех видов топлива в одном контракте"""
        return sum(item.required_quantity for item in self.items.all())

    class Meta:
        verbose_name = "Тендер / Контракт"
        verbose_name_plural = "Биржа тендеров"


class OrderItem(models.Model):
    """Позиции внутри конкретного тендера (Бензин, Мазут, Дизель и т.д.)"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Тендер")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Требуемый продукт")
    required_quantity = models.FloatField(verbose_name="Необходимый объем (т)")

    def __str__(self):
        return f"{self.product.name} — {self.required_quantity} т."

    class Meta:
        verbose_name = "Товар в тендере"
        verbose_name_plural = "Товары в тендере"


# ==========================================================
# 11. ЗАРПЛАТА
# ==========================================================
class SalaryPayment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Работник")
    amount = models.FloatField(verbose_name="Сумма выплаты (USD)")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Выплата зарплаты"
        verbose_name_plural = "Выплаты зарплаты"


# ==========================================================
# ⚙️ СИГНАЛЫ (АВТОМАТИЗАЦИЯ СКЛАДА)
# ==========================================================
@receiver(post_save, sender=Purchase)
def process_purchase(sender, instance, created, **kwargs):
    if created:
        finance = Finance.objects.first()
        if finance:
            finance.balance -= instance.total_price
            finance.expenses += instance.total_price
            finance.save()

        storage, _ = RawStorage.objects.get_or_create(
            oil_material=instance.oil,
            defaults={'capacity': 10000}
        )
        storage.current_volume += instance.volume
        storage.save()