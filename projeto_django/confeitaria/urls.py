from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.autenticar_login, name='autenticar_login'),
    path('usuario/cadastrar', views.criar_usuario, name='criar_usuario'),
    path('menu/', views.menu, name='menu'),
    path('menuusuario/', views.menu_usuario, name='menu_usuario'),
    
    path('produtos/', views.listar_produto, name='listar_produto'),
    path('produto/cadastro/', views.criar_produto, name='criar_produto'),
    path('produto/<int:id>/editar/', views.editar_produto, name='editar_produto'),
    path('produtos/editar_modal/<int:id>/', views.editar_produto_modal, name='editar_produto_modal'),
    path('produtos/<int:id>/deletar/', views.deletar_produto,name='deletar_produto'),
    
    path('clientes/', views.listar_cliente, name='listar_cliente'),
    path('clientes/cadastro/', views.criar_cliente, name='criar_cliente'),
    path('clientes/<int:id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:id>/deletar/', views.deletar_cliente,name='deletar_cliente'),
    
    path('pedido/cadastro/', views.criar_pedido, name='criar_pedido'), 
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('pedido/<int:pedido_id>/marcar_pronto/', views.marcar_pronto, name='marcar_pronto'),
    path('pedido/<int:pedido_id>/concluir/', views.confirmar_pagamento, name='confirmar_pagamento'),

    path('relatorios/vendas/', views.relatorio_vendas, name='relatorio_vendas'),
    path('relatorios/gerar_pdf/', views.gerar_pdf_relatorio_vendas, name='gerar_pdf_relatorio_vendas'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)