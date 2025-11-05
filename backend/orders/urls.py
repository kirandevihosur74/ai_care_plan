from django.urls import path
from . import views
urlpatterns = [
    path('validate', views.validate_order, name='validate_order'),
    path('generate', views.generate_order, name='generate_order'),
    path('', views.get_orders, name='get_orders'),
    path('<int:order_id>', views.get_order, name='get_order'),
    path('export/all', views.export_all_care_plans, name='export_all_care_plans'),
]