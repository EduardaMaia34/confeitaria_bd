from django.urls import path
from . import views

urlpatterns = [
    path('', views.autenticar_login, name='autenticar_login'),
    path('menu/', views.menu, name='menu'),
    
    path('produtos/', views.listar_produto, name='listar_produto'),
    path('produto/cadastro/', views.criar_produto, name='criar_produto'),
    path('produto/<int:id>/editar/', views.editar_produto, name='editar_produto'),
    path('produtos/<int:id>/deletar/', views.deletar_produto,name='deletar_produto'),
    
    path('clientes/', views.listar_cliente, name='listar_cliente'),
    path('clientes/cadastro/', views.criar_cliente, name='criar_cliente'),
    path('clientes/<int:id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:id>/deletar/', views.deletar_cliente,name='deletar_cliente'),
    
    path('pedido/cadastro', views.criar_pedido, name='criar_pedido'),
    path('pedido/<int:id_pedido>/adicionar_produto/', views.adicionar_produto_ao_pedido, name='adicionar_produto_ao_pedido'),
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
]