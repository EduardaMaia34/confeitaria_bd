from django.urls import path
from .views import criar_produto, criar_cliente

urlpatterns = [
    path("", menu, name='menu'),
    path("", criar_produto, name="criar_produto"),
    path("", criar_cliente, name="criar_cliente"),
]
