from django.contrib import admin
from django.urls import path, include
from orders import views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.api_root, name='api_root'),
    path('api/orders/', include('orders.urls')),
]