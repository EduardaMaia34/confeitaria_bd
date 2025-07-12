from django.urls import path
from . import views

urlpatterns = [
    path('', views.autenticar_login, name='autenticar_login'),
    path('menu', views.menu, name='menu'),
    path('produto/cadastro/', views.criar_produto, name='criar_produto'),
    path('cliente/cadastro/', views.criar_cliente, name='criar_cliente'),
    path('pedido/cadastro', views.criar_pedido, name='criar_pedido'),
    path('pedido/<int:id_pedido>/adicionar_produto/', views.adicionar_produto_ao_pedido, name='adicionar_produto_ao_pedido'),
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
]
