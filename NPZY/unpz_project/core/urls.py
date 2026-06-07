from django.urls import path
from . import views

urlpatterns = [
    # Главная панель управления
    path('', views.index, name='index'),

    # Логистика и закупки
    path('purchase/', views.purchase_oil, name='purchase_oil'),
    path('purchase/success/', views.purchase_success, name='purchase_success'),

    # Производственный цех
    path('produce/', views.produce_oil, name='produce_oil'),

    # Модуль продаж (розница и опт)
    path('sell/', views.sell_product, name='sell_product'),

    # Модуль тендеров и контрактов (АЗС)
    path('orders/', views.order_list, name='order_list'),
    path('orders/fulfill/<int:order_id>/', views.fulfill_order, name='fulfill_order'),
    path('receipt/<int:sale_id>/', views.view_receipt, name='view_receipt'),

    # Финансы (зарплаты и отчёты бухгалтера)
    path('salaries/', views.pay_salaries, name='pay_salaries'),
    path('reports/', views.accountant_reports, name='accountant_reports'),

    # Генерация и скачивание PDF отчёта
    path('reports/pdf/', views.export_pdf_report, name='export_pdf_report'),
]