from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm
from .models import Pedido, Cliente, Produto, PedidoProduto

def menu(request):
    return render(request, 'confeitaria/menu.html')

def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('criar_produto')  # ou uma página de sucesso
    else:
        form = ProdutoForm()
    return render(request, 'confeitaria/cadastrar_produto.html', {'form': form})


def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('criar_cliente')  # ou uma página de sucesso
    else:
        form = ClienteForm()
    return render(request, 'confeitaria/cadastrar_cliente.html', {'form': form})

def criar_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)  # <- IMPORTANTE
    else:
        form = PedidoForm()
    return render(request, 'confeitaria/cadastrar_pedido.html', {'form': form})

def adicionar_produto_ao_pedido(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido)

    if request.method == 'POST':
        form = PedidoProdutoForm(request.POST)
        if form.is_valid():
            pedido_produto = form.save(commit=False)
            pedido_produto.id_pedido = pedido  # associa ao pedido existente
            pedido_produto.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
    else:
        form = PedidoProdutoForm()

    return render(request, 'confeitaria/adicionar_produto.html', {
    'pedido': pedido,
    'form': form
    })

def listar_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-data_pedido') # Added ordering for better display
    return render(request, 'confeitaria/lista_pedidos.html', {'pedidos': pedidos})