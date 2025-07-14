from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm, UsuarioForm
from .models import Pedido, Cliente, Produto, PedidoProduto, Usuario
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection


def menu(request):
    return render(request, 'confeitaria/menu.html')

def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)  # Inclui request.FILES para upload de imagens
        if form.is_valid():
            form.save()
            return redirect('listar_produto')  # ou uma página de sucesso
    else:
        form = ProdutoForm()
    return render(request, 'confeitaria/cadastrar_produto.html', {'form': form})


def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_cliente')  # ou uma página de sucesso
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

def autenticar_login(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user_input  = request.POST.get('usuario')
            pwd_input   = request.POST.get('senha')

            with connection.cursor() as cur:
                cur.execute(
                    "SELECT senha FROM confeitaria_usuario WHERE usuario = %s",
                    [user_input]
                )
                row = cur.fetchone()

            if row and pwd_input == row[0]:
                User = get_user_model()
                django_user, _ = User.objects.get_or_create(
                    username=user_input, defaults={"is_active": True}
                )
                django_login(request, django_user)  # cria sessão
                return redirect("menu")

            messages.error(request, "Usuário ou senha incorretos.")
    else:
        form = UsuarioForm()

    return render(request, "confeitaria/login.html", {"form": form})

def listar_cliente(request):
    termo = request.GET.get('q', '')
    if termo:
        clientes = Cliente.objects.filter(nome__icontains=termo)
    else:
        clientes = Cliente.objects.all()
    
    return render(request, 'confeitaria/clientes.html', {'clientes': clientes})

def listar_produto(request):
    termo = request.GET.get('q', '')
    if termo:
        produtos = Produto.objects.filter(nome__icontains=termo)
    else:
        produtos = Produto.objects.all()
    
    return render(request, 'confeitaria/interface_produto.html', {'produtos': produtos})


def editar_produto(request, id): 
    produto = get_object_or_404(Produto, id=id)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto) 
        if form.is_valid():
            form.save()
            return redirect('listar_produto') 
    else:
       
        form = ProdutoForm(instance=produto)

    return render(request, 'confeitaria/editar_produto.html', {'form': form})

def editar_produto_modal(request, id):
    produto = get_object_or_404(Produto, id=id)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'form_html': render(request, 'confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto}).content.decode('utf-8')})
    else:
        form = ProdutoForm(instance=produto)
    
    return render(request, 'confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto})

    return render(request, 'confeitaria/editar_produto.html', {'form': form, 'produto': produto})

def deletar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)

    if request.method == "POST":
        produto.delete()
        return redirect("listar_produto")          # volta para a lista

    # GET → exibe confirmação
    return render(request, "confeitaria/deletar_produto.html", {"produto": produto})


def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('listar_cliente')  # Redireciona para listagem
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'confeitaria/editar_cliente.html', {'form': form, 'cliente': cliente})

def deletar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == "POST":
        cliente.delete()
        return redirect("listar_cliente")          # volta para a lista

    # GET → exibe confirmação
    return render(request, "confeitaria/deletar_cliente.html", {"cliente": cliente})