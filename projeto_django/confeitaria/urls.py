from django.urls import path
from .views import criar_produto, criar_cliente, menu

urlpatterns = [
    path('', menu, name='menu'),
    path("produto/cadastro/", criar_produto, name="criar_produto"),
    path("cliente/cadastro/", criar_cliente, name="criar_cliente"),
]
