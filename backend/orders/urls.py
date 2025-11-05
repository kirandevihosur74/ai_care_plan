from django.urls import path
from . import views
urlpatterns = [
    path('validate', views.validate_order, name='validate_order'),
    path('generate', views.generate_order, name='generate_order'),
    path('export/all', views.export_all_care_plans, name='export_all_care_plans'),
    path('export/stats', views.export_stats, name='export_stats'),
    path('export', views.export_orders, name='export_orders'),
    path('<int:order_id>', views.get_order, name='get_order'),
    path('', views.get_orders, name='get_orders'),
]