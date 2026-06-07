import json
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.template.loader import render_to_string
from django.utils import timezone
from .models import RawMaterial, Purchase, Finance, RawStorage, Product, ProductStorage, Employee, Sale, Order, \
    OrderItem

# Безопасный импорт WeasyPrint для работы на любой операционной системе (Windows/Linux)
try:
    from weasyprint import HTML
except (ImportError, OSError):
    HTML = None

# ==========================================================
# ⚙️ УМНЫЙ КОНФИГУРАТОР ТЕХНОЛОГИЙ (TECH_CONFIG)
# ==========================================================
TECH_CONFIG = {
    'light': {
        'max_gas': {
            'name': '🚀 Максимум бензина (АИ-98)',
            'yields': {'Бензин АИ-98': 60, 'Дизель': 20, 'Керосин': 10, 'Мазут': 7, 'Потери': 3}
        },
        'max_diesel': {
            'name': '🚚 Максимум дизеля (Евро-5)',
            'yields': {'Бензин АИ-95': 20, 'Дизель': 65, 'Керосин': 5, 'Мазут': 8, 'Потери': 2}
        },
        'zero_waste': {
            'name': '🍃 Безотходный цикл (Глубокий крекинг)',
            'yields': {'Бензин': 35, 'Дизель': 35, 'Битум': 20, 'Газ': 10, 'Потери': 0}
        }
    },
    'medium': {
        'standard': {
            'name': '⚙️ Стандартная ректификация',
            'yields': {'Бензин АИ-92': 30, 'Дизель': 30, 'Мазут': 35, 'Потери': 5}
        },
        'bitumen': {
            'name': '🛣️ Дорожный вектор (Битум)',
            'yields': {'Мазут': 40, 'Битум': 40, 'Дизель': 15, 'Потери': 5}
        }
    },
    'heavy': {
        'deep': {
            'name': '🏗️ Глубокая переработка (с ГК)',
            'yields': {'Пропан-Бутан': 5, 'Бензин АИ-95': 25, 'Дизель': 30, 'Мазут': 15, 'Асфальт': 22, 'Потери': 3}
        }
    }
}

# ==========================================================
# 📊 СПРАВОЧНИК РЫНОЧНЫХ ЦЕН (USD за тонну)
# ==========================================================
MARKET_PRICES = {
    'Бензин АИ-98': {'retail': 1200.0, 'wholesale': 1050.0},
    'Бензин АИ-95': {'retail': 1100.0, 'wholesale': 950.0},
    'Бензин АИ-92': {'retail': 1000.0, 'wholesale': 850.0},
    'Дизель': {'retail': 900.0, 'wholesale': 780.0},
    'Керосин': {'retail': 950.0, 'wholesale': 820.0},
    'Пропан-Бутан': {'retail': 600.0, 'wholesale': 500.0},
    'Мазут': {'retail': 450.0, 'wholesale': 380.0},
    'Битум': {'retail': 500.0, 'wholesale': 420.0},
    'Асфальт': {'retail': 300.0, 'wholesale': 250.0},
    'Газ': {'retail': 550.0, 'wholesale': 480.0},
    'Бензин': {'retail': 950.0, 'wholesale': 800.0},
}

PROCESSING_COST_PER_TON = 50.0


def access_denied_response(request, required_role_name):
    try:
        current_role = request.user.employee.get_role_display()
    except Employee.DoesNotExist:
        current_role = "Не определена"

    return render(request, 'core/orders.html', {
        'finance': Finance.objects.first(),
        'gov_tenders': [o for o in Order.objects.filter(status='open').prefetch_related('items__product') if
                        o.total_quantity >= 30.0],
        'private_orders': [o for o in Order.objects.filter(status='open').prefetch_related('items__product') if
                           o.total_quantity < 30.0],
        'error': f'Доступ запрещен! Ваша текущая должность: "{current_role}". Данное действие может выполнять только {required_role_name}.'
    })


# 1. ГЛАВНАЯ ПАНЕЛЬ
def index(request):
    finance = Finance.objects.first()
    if not finance:
        finance = Finance.objects.create(balance=1000000)

    user_role = "Администратор"
    employee = None
    if request.user.is_authenticated:
        try:
            employee = request.user.employee
            user_role = employee.get_role_display()
        except Employee.DoesNotExist:
            pass

    return render(request, 'core/index.html', {
        'finance': finance,
        'stocks': RawStorage.objects.all(),
        'product_stocks': ProductStorage.objects.all(),
        'user_role': user_role,
        'employee': employee
    })


# ==========================================================
# 🛒 БЛОК ЗАКУПОК (С ПРЕДПРОСМОТРОМ И ПОДТВЕРЖДЕНИЕМ ЧЕКА)
# ==========================================================
@login_required
def purchase_oil(request):
    try:
        employee = request.user.employee
        if employee.role != 'purchaser' and employee.role != 'admin':
            return access_denied_response(request, 'Менеджер по закупкам')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Менеджер по закупкам')

    materials = RawMaterial.objects.all()
    finance = Finance.objects.first()

    if request.method == "POST":
        if "confirm_action" in request.POST:
            action = request.POST.get("action")
            if action == "save":
                oil_id = request.POST.get('oil_id')
                volume = float(request.POST.get('volume', 0))
                total_cost = float(request.POST.get('total_cost', 0))
                supplier = request.POST.get('supplier', 'Global Oil Trading')

                if finance.balance >= total_cost:
                    oil = RawMaterial.objects.get(id=oil_id)
                    Purchase.objects.create(oil=oil, volume=volume, total_price=total_cost, supplier=supplier)

                    raw_storage, _ = RawStorage.objects.get_or_create(
                        oil_material=oil,
                        defaults={'capacity': 10000.0, 'current_volume': 0.0}
                    )
                    raw_storage.current_volume += volume
                    raw_storage.save()

                    finance.balance -= total_cost
                    finance.expenses += total_cost
                    finance.save()
                    return redirect('index')
                else:
                    return render(request, 'core/purchase.html', {
                        'materials': materials, 'finance': finance, 'error': 'Недостаточно денег на балансе!'
                    })
            else:
                return redirect('purchase_oil')

        oil_id = request.POST.get('oil_id')
        vol_raw = request.POST.get('volume')
        try:
            volume = float(vol_raw) if vol_raw else 0
        except ValueError:
            volume = 0

        if oil_id and volume > 0:
            oil = RawMaterial.objects.get(id=oil_id)
            total_cost = oil.price_per_ton * volume
            supplier = request.POST.get('supplier', 'Global Oil Trading')

            return render(request, 'core/preview_receipt.html', {
                'type': 'purchase',
                'title': '🧾 Чек на закупку сырья',
                'item_name': oil.name,
                'volume': volume,
                'price_per_unit': oil.price_per_ton,
                'total_cost': total_cost,
                'extra_info': f'Поставщик: {supplier}',
                'passthrough_data': {
                    'oil_id': oil_id,
                    'volume': volume,
                    'total_cost': total_cost,
                    'supplier': supplier
                }
            })

    return render(request, 'core/purchase.html', {'materials': materials, 'finance': finance})


# ==========================================================
# ⚙️ БЛОК ПРОИЗВОДСТВА (ЗАЩИЩЕН ОТ НУЛЕВОГО СОХРАНЕНИЯ ТОЛЬКО ЧТО ПРОИЗВЕДЕННОГО ТОВАРА)
# ==========================================================
@login_required
def produce_oil(request):
    try:
        employee = request.user.employee
        if employee.role != 'technologist' and employee.role != 'admin':
            return access_denied_response(request, 'Технолог')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Технолог')

    stocks = RawStorage.objects.all()
    finance = Finance.objects.first()

    if request.method == "POST":
        if "confirm_action" in request.POST:
            action = request.POST.get("action")
            if action == "save":
                oil_id = request.POST.get('oil_id')
                tech_id = request.POST.get('tech_id')

                # Валидация объема. Если фронтенд прислал пустоту или 0 — сбрасываем операцию, чтобы не затереть склад
                try:
                    amount = float(request.POST.get('amount', 0))
                except (ValueError, TypeError):
                    amount = 0

                if amount <= 0:
                    return redirect('produce_oil')

                storage = RawStorage.objects.get(oil_material_id=oil_id)
                raw_material = storage.oil_material

                if storage.current_volume >= amount:
                    storage.current_volume -= amount
                    storage.save()

                    total_proc_cost = amount * PROCESSING_COST_PER_TON
                    finance.balance -= total_proc_cost
                    finance.expenses += total_proc_cost
                    finance.save()

                    cost_per_ton_raw = raw_material.price_per_ton + PROCESSING_COST_PER_TON
                    raw_db_type = raw_material.oil_type.lower()
                    oil_key = 'light' if 'light' in raw_db_type else ('heavy' if 'heavy' in raw_db_type else 'medium')
                    selected_tech = TECH_CONFIG[oil_key][tech_id]

                    for prod_name, percent in selected_tech['yields'].items():
                        if prod_name == 'Потери':
                            continue

                        volume_out = amount * (percent / 100)
                        prices = MARKET_PRICES.get(prod_name, {'retail': 800.0, 'wholesale': 650.0})

                        name_lower = prod_name.lower()
                        if '98' in name_lower or '95' in name_lower:
                            coef = 1.25
                        elif '92' in name_lower or 'бензин' in name_lower:
                            coef = 1.15
                        elif 'дизель' in name_lower or 'керосин' in name_lower:
                            coef = 1.05
                        elif 'газ' in name_lower or 'пропан' in name_lower:
                            coef = 0.85
                        else:
                            coef = 0.60

                        calculated_production_cost = round(cost_per_ton_raw * coef, 2)

                        product, created = Product.objects.get_or_create(
                            name=prod_name,
                            defaults={
                                'price_retail': prices['retail'],
                                'price_wholesale': prices['wholesale'],
                                'production_cost': calculated_production_cost,
                                'type': 'Топливо'
                            }
                        )

                        if not created:
                            product.production_cost = calculated_production_cost
                            product.price_retail = prices['retail']
                            product.price_wholesale = prices['wholesale']
                            product.save()

                        # Накопительное сохранение объема на складе готовой продукции
                        prod_storage, _ = ProductStorage.objects.get_or_create(
                            product=product,
                            defaults={'capacity': 5000.0, 'quantity': 0.0}
                        )
                        prod_storage.quantity += volume_out
                        prod_storage.save()

                    return redirect('index')
            else:
                return redirect('produce_oil')

        oil_id = request.POST.get('oil_id')
        tech_id = request.POST.get('tech_id')
        try:
            amount = float(request.POST.get('amount', 0))
        except (ValueError, TypeError):
            amount = 0

        if oil_id and tech_id and amount > 0:
            storage = RawStorage.objects.get(oil_material_id=oil_id)
            raw_material = storage.oil_material

            raw_db_type = raw_material.oil_type.lower()
            oil_key = 'light' if 'light' in raw_db_type else ('heavy' if 'heavy' in raw_db_type else 'medium')
            selected_tech = TECH_CONFIG.get(oil_key, {}).get(tech_id)

            if selected_tech and storage.current_volume >= amount:
                preview_yields = []
                cost_per_ton_raw = raw_material.price_per_ton + PROCESSING_COST_PER_TON

                for prod_name, percent in selected_tech['yields'].items():
                    if prod_name == 'Потери':
                        continue
                    name_lower = prod_name.lower()
                    coef = 1.25 if '98' in name_lower or '95' in name_lower else (
                        1.15 if '92' in name_lower or 'бензин' in name_lower else (
                            1.05 if 'дизель' in name_lower or 'керосин' in name_lower else (
                                0.85 if 'газ' in name_lower or 'пропан' in name_lower else 0.60)))

                    preview_yields.append({
                        'name': prod_name,
                        'volume': amount * (percent / 100),
                        'cost': round(cost_per_ton_raw * coef, 2)
                    })

                return render(request, 'core/preview_receipt.html', {
                    'type': 'production',
                    'title': '🏭 Акт приёма-переработки сырья',
                    'item_name': raw_material.name,
                    'volume': amount,
                    'extra_info': f'Технология: {selected_tech["name"]}',
                    'preview_yields': preview_yields,
                    'total_cost': amount * PROCESSING_COST_PER_TON,
                    'passthrough_data': {'oil_id': oil_id, 'tech_id': tech_id, 'amount': amount}
                })

    return render(request, 'core/produce.html', {'stocks': stocks, 'yield_map_json': json.dumps(TECH_CONFIG)})


# ==========================================================
# 💰 БЛОК ПРОДАЖ (С ПРЕДПРОСМОТРОМ И ПОДТВЕРЖДЕНИЕМ ЧЕКА)
# ==========================================================
@login_required
def sell_product(request):
    try:
        employee = request.user.employee
        if employee.role != 'sales' and employee.role != 'admin':
            return access_denied_response(request, 'Менеджер по продажам')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Менеджер по продажам')

    p_stocks = ProductStorage.objects.all()
    finance = Finance.objects.first()

    if request.method == "POST":
        if "confirm_action" in request.POST:
            action = request.POST.get("action")
            if action == "save":
                ps_id = request.POST.get('ps_id')
                qty = float(request.POST.get('quantity', 0))
                mode = request.POST.get('mode')
                client = request.POST.get('client', 'Неизвестный покупатель')

                ps = ProductStorage.objects.get(id=ps_id)
                if ps.quantity >= qty:
                    price = ps.product.price_retail if mode == 'retail' else ps.product.price_wholesale
                    revenue_raw = price * qty
                    tax = revenue_raw * 0.12
                    revenue_net = revenue_raw - tax

                    ps.quantity -= qty
                    ps.save()

                    finance.balance += revenue_net
                    finance.income += revenue_net
                    finance.save()

                    Sale.objects.create(product=ps.product, quantity=qty, total_price=revenue_raw, sale_type=mode,
                                        client=client)
                    return redirect('index')
            else:
                return redirect('sell_product')

        ps_id = request.POST.get('ps_id')
        qty = float(request.POST.get('quantity', 0))
        mode = request.POST.get('mode')
        client = request.POST.get('client', 'Неизвестный покупатель')

        if ps_id and qty > 0:
            ps = ProductStorage.objects.get(id=ps_id)
            if ps.quantity >= qty:
                price = ps.product.price_retail if mode == 'retail' else ps.product.price_wholesale
                total_cost = price * qty
                return render(request, 'core/preview_receipt.html', {
                    'type': 'sale',
                    'title': '💸 Товарный чек продажи готовой продукции',
                    'item_name': ps.product.name,
                    'volume': qty,
                    'price_per_unit': price,
                    'total_cost': total_cost,
                    'extra_info': f'Клиент: {client} ({mode.upper()})',
                    'passthrough_data': {'ps_id': ps_id, 'quantity': qty, 'mode': mode, 'client': client}
                })

    return render(request, 'core/sell.html', {'p_stocks': p_stocks, 'finance': finance})


# ==========================================================
# 📈 БИРЖА ОПТА И ТЕНДЕРОВ
# ==========================================================
@login_required
def order_list(request):
    finance = Finance.objects.first()
    open_orders = Order.objects.filter(status='open').prefetch_related('items__product')
    return render(request, 'core/orders.html', {
        'gov_tenders': [o for o in open_orders if o.total_quantity >= 30.0],
        'private_orders': [o for o in open_orders if o.total_quantity < 30.0],
        'finance': finance
    })


@login_required
def fulfill_order(request, order_id):
    try:
        employee = request.user.employee
        if employee.role != 'sales' and employee.role != 'admin':
            return access_denied_response(request, 'Менеджер по продажам')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Менеджер по продажам')

    order = Order.objects.get(id=order_id)
    finance = Finance.objects.first()

    for item in order.items.all():
        ps = ProductStorage.objects.get(product=item.product)
        if ps.quantity < item.required_quantity:
            return redirect('order_list')

    last_sale = None
    total_items = order.items.count()

    for item in order.items.all():
        ps = ProductStorage.objects.get(product=item.product)
        ps.quantity -= item.required_quantity
        ps.save()

        distributed_price = order.reward_price / total_items if total_items > 0 else 0
        last_sale = Sale.objects.create(product=item.product, quantity=item.required_quantity,
                                        total_price=distributed_price, sale_type='wholesale',
                                        client=order.customer_name)

    revenue_net = order.reward_price * 0.88
    finance.balance += revenue_net
    finance.income += revenue_net
    finance.save()

    order.status = 'completed'
    order.save()
    return redirect('view_receipt', sale_id=last_sale.id)


def view_receipt(request, sale_id):
    sale = Sale.objects.get(id=sale_id)
    margin = sale.total_price - (sale.product.production_cost * sale.quantity)
    return render(request, 'core/receipt.html', {'sale': sale, 'margin': margin})


# ==========================================================
# 🧾 БЛОК ВЫДАЧИ ЗАРАБОТНОЙ ПЛАТЫ С ПОДТВЕРЖДЕНИЕМ ВЕДОМОСТИ
# ==========================================================
@login_required
def pay_salaries(request):
    try:
        employee = request.user.employee
        if employee.role != 'accountant' and employee.role != 'admin':
            return access_denied_response(request, 'Бухгалтер')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Бухгалтер')

    finance = Finance.objects.first()
    employees = Employee.objects.all()

    total_purchases_sum = Purchase.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_sales_sum = Sale.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_production_cost = sum(sale.product.production_cost * sale.quantity for sale in Sale.objects.all())

    salary_table = []
    total_payout = 0

    if request.method == "POST" and "confirm_payout" in request.POST:
        action = request.POST.get("action")
        if action == "save":
            for emp in employees:
                emp_final = float(request.POST.get(f'final_payout_{emp.id}', 0))
                total_payout += emp_final

            if finance.balance >= total_payout:
                finance.balance -= total_payout
                finance.expenses += total_payout
                finance.save()
                return redirect('index')
            else:
                return redirect('pay_salaries')
        else:
            return redirect('pay_salaries')

    if request.method == "POST" and "preview_payroll" in request.POST:
        preview_rows = []
        for emp in employees:
            custom_base = float(request.POST.get(f'base_{emp.id}', emp.salary))
            days = int(request.POST.get(f'days_{emp.id}', 22))
            kpi_type = request.POST.get(f'kpi_type_{emp.id}', 'fixed')
            kpi_val = float(request.POST.get(f'kpi_val_{emp.id}', 0))

            calc_base = custom_base * (days / 22)
            calc_kpi = kpi_val if kpi_type == 'fixed' else (
                total_purchases_sum * (kpi_val / 100) if kpi_type == 'purchases' else (
                    total_production_cost * (kpi_val / 100) if kpi_type == 'production' else total_sales_sum * (
                                kpi_val / 100)))

            row_total = calc_base + calc_kpi
            total_payout += row_total

            preview_rows.append({
                'employee': emp, 'calculated_base': calc_base, 'bonus': calc_kpi, 'total': row_total
            })

        return render(request, 'core/preview_receipt.html', {
            'type': 'salary',
            'title': '🧾 Расчётно-платёжная ведомость ЗП',
            'preview_yields': preview_rows,
            'total_cost': total_payout,
            'passthrough_data': {'dummy': '1'}
        })

    for emp in employees:
        salary_table.append({
            'employee': emp, 'base': float(emp.salary), 'days': 22, 'kpi_type': 'fixed', 'kpi_val': 0.0,
            'calculated_base': float(emp.salary), 'bonus': 0.0, 'total': float(emp.salary)
        })
        total_payout += float(emp.salary)

    return render(request, 'core/salaries.html', {
        'salary_table': salary_table, 'total': total_payout, 'finance': finance,
        'total_purchases': total_purchases_sum, 'total_production': total_production_cost,
        'total_sales': total_sales_sum
    })


# ==========================================================
# 📊 ЕДИНЫЙ ЦЕНТР ОТЧЁТНОСТИ ПО ЗАКУПКАМ И ПРОДАЖАМ + СКАЧИВАНИЕ PDF
# ==========================================================
@login_required
def accountant_reports(request):
    try:
        employee = request.user.employee
        if employee.role != 'accountant' and employee.role != 'admin':
            return access_denied_response(request, 'Бухгалтер')
    except Employee.DoesNotExist:
        if not request.user.is_superuser:
            return access_denied_response(request, 'Бухгалтер')

    purchases = Purchase.objects.all().order_by('-date')
    sales = Sale.objects.all().order_by('-date')

    total_spent_oil = purchases.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_earned_sales = sales.aggregate(Sum('total_price'))['total_price__sum'] or 0

    return render(request, 'core/reports.html', {
        'purchases': purchases,
        'sales': sales,
        'total_spent_oil': total_spent_oil,
        'total_earned_sales': total_earned_sales,
        'finance': Finance.objects.first()
    })


@login_required
def export_pdf_report(request):
    """
    Генерирует и отдаёт на скачивание PDF-версию отчёта бухгалтера
    """
    if not HTML:
        return render(request, 'core/reports.html', {
            'purchases': Purchase.objects.all().order_by('-date'),
            'sales': Sale.objects.all().order_by('-date'),
            'finance': Finance.objects.first(),
            'error': 'Ошибка генерации: Системные библиотеки GTK+ или WeasyPrint не настроены на сервере Windows! Скачайте GTK-for-Windows.'
        })

    purchases = Purchase.objects.all().order_by('-date')
    sales = Sale.objects.all().order_by('-date')
    finance = Finance.objects.first()

    context = {
        'purchases': purchases,
        'sales': sales,
        'finance': finance,
        'current_time': timezone.now()
    }

    html_string = render_to_string('core/pdf_report_template.html', context)

    pdf_file = io.BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)

    return FileResponse(pdf_file, as_attachment=True,
                        filename=f"unpz_financial_report_{timezone.now().strftime('%d_%m_%Y')}.pdf")


def purchase_success(request):
    return render(request, 'core/purchase_success.html')