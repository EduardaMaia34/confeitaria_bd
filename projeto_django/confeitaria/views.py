from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm, UsuarioForm
from .models import Pedido, Cliente, Produto, PedidoProduto, Usuario
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection
from django.utils.dateparse import parse_date
from django.db.models import Sum


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
            nome = form.cleaned_data['nome']
            telefone = form.cleaned_data['telefone']

            # Verifica se já existe cliente com o mesmo nome e telefone
            if Cliente.objects.filter(nome=nome, telefone=telefone).exists():
                messages.warning(request, "Cliente já existente.")
                return render(request, 'confeitaria/cadastrar_cliente.html', {'form': form})

            try:
                form.save()
                messages.success(request, "Cliente cadastrado com sucesso!")
                return redirect('listar_cliente')
            except Exception as e:
                messages.error(request, "Erro: não foi possível cadastrar o cliente.")
        else:
            messages.warning(request, "Dados inválidos. Verifique os campos.")
    else:
        form = ClienteForm()

    return render(request, 'confeitaria/cadastrar_cliente.html', {'form': form})


def criar_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
    else:
        form = PedidoForm()
    return render(request, 'confeitaria/cadastrar_pedido.html', {'form': form})


def adicionar_produto_ao_pedido(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido)
    produtos = Produto.objects.all()

    if request.method == 'POST':
        form = PedidoProdutoForm(request.POST)
        if form.is_valid():
            pedido_produto = form.save(commit=False)
            pedido_produto.id_pedido = pedido
            pedido_produto.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
    else:
        form = PedidoProdutoForm()

    return render(request, 'confeitaria/adicionar_produto.html', {
        'pedido': pedido,
        'form': form,
        'produtos': produtos
    })


def listar_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-data_pedido')
    return render(request, 'confeitaria/interfacePedidos.html', {'pedidos': pedidos})

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
    
    return render(request, 'confeitaria/interfaceClientes.html', {'clientes': clientes})

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

def relatorio_vendas(request):
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    vendas = Pedido.objects.all().order_by('-data_pedido')

    if data_inicial and data_final:
        try:
            data_inicio = parse_date(data_inicial)
            data_fim = parse_date(data_final)
            vendas = vendas.filter(data_pedido__range=[data_inicio, data_fim])
        except:
            messages.warning(request, "Formato de data inválido.")

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0

    return render(request, 'confeitaria/relatorio_vendas.html', {
        'vendas': vendas,
        'data_inicial': data_inicial,
        'data_final': data_final,
        'total': total
    })