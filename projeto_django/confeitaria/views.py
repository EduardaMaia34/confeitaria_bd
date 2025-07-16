from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm, UsuarioForm, PedidoProdutoFormSet
from .models import Pedido, Cliente, Produto, PedidoProduto, Usuario
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.template.loader import render_to_string
from django.db.models import Q

def is_gerente(user):
    
    return user.groups.filter(name='Gerentes').exists() or user.is_superuser or user.username == 'admin'

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

    itens_do_pedido = PedidoProduto.objects.filter(id_pedido=pedido)
    produtos = Produto.objects.all()


    if request.method == 'POST':
        form = PedidoProdutoForm(request.POST)
        if form.is_valid():
            pedido_produto = form.save(commit=False)
            pedido_produto.id_pedido = pedido
            pedido_produto.save()
            messages.success(request, f"Produto '{pedido_produto.id_produto.nome}' adicionado com sucesso!")
            # After saving, redirect to the same page to show the updated list
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
        else:
            messages.error(request, "Erro ao adicionar produto. Verifique os dados.")
    else:
        form = PedidoProdutoForm()

    return render(request, 'confeitaria/adicionar_produto.html', {
        'pedido': pedido,
        'form': form,

        'itens_do_pedido': itens_do_pedido, # <--- Pass the list of items
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

@login_required
def listar_produto(request):
    
    search_query = request.GET.get('q', '').strip()

    produtos = Produto.objects.all()

    if search_query:
        produtos = produtos.filter(
            Q(nome__icontains=search_query) | Q(descricao__icontains=search_query)
        )

    usuario_eh_gerente = is_gerente(request.user) # Keep your existing manager check

    context = {
        'produtos': produtos,
        'is_gerente': usuario_eh_gerente,
        'search_query': search_query,
    }
    
    return render(request, 'confeitaria/interface_produto.html', context)




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


#PEDIDOS
def criar_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)  # <- IMPORTANTE
    else:
        form = PedidoForm()
    return render(request, 'confeitaria/cadastrar_pedido.html', {'form': form})

def listar_pedidos(request):
    q = request.GET.get('q', '')
    if q:
        pedidos = Pedido.objects.filter(cliente__nome__icontains=q).order_by('-data_pedido')
    else:
        pedidos = Pedido.objects.all().order_by('-data_pedido')

    return render(request, 'confeitaria/interface_pedido.html', {'pedidos': pedidos})


def editar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)

    add_product_form = PedidoProdutoForm()

    if request.method == 'POST':
        if 'add_new_product' in request.POST:
            add_product_form = PedidoProdutoForm(request.POST)
            if add_product_form.is_valid():
                produto_a_adicionar = add_product_form.cleaned_data['id_produto']
                quantidade_a_adicionar = add_product_form.cleaned_data['quantidade']

                try:
                    pedido_produto_existente = PedidoProduto.objects.get(
                        id_pedido=pedido,
                        id_produto=produto_a_adicionar
                    )
                    pedido_produto_existente.quantidade += quantidade_a_adicionar
                    pedido_produto_existente.save()
                    messages.success(request, f"Quantidade do produto '{produto_a_adicionar.nome}' atualizada para {pedido_produto_existente.quantidade}.")

                except PedidoProduto.DoesNotExist:
                    new_item = add_product_form.save(commit=False)
                    new_item.id_pedido = pedido
                    new_item.save()
                    messages.success(request, f"Produto '{new_item.id_produto.nome}' adicionado ao pedido.")
                
                return redirect('editar_pedido', id=pedido.id)

            else:
                messages.error(request, "Dados inválidos para adicionar produto.")
        
        elif 'save_existing_items' in request.POST:
            item_formset = PedidoProdutoFormSet(request.POST, instance=pedido)
            if item_formset.is_valid():
                item_formset.save()
                messages.success(request, "Produtos do pedido atualizados com sucesso!")
                return redirect('listar_pedidos')
            else:
                
                print("--- Formset Validation Errors ---")
                print("Non-form errors:", item_formset.non_form_errors()) # Errors not tied to a specific form (e.g., total forms limit)
                for i, form in enumerate(item_formset):
                    if form.errors:
                        print(f"Form {i} errors (Prefix: {form.prefix}):", form.errors)
                        for field, errors in form.errors.items():
                            print(f"  Field '{field}': {errors}")
                print("---------------------------------")
                messages.error(request, "Houve um erro ao salvar os produtos do pedido. Por favor, verifique os campos.")
                
        elif 'remove_item' in request.POST:
            pedido_produto_id = request.POST.get('pedido_produto_id')
            if pedido_produto_id:
                try:
                    item_to_delete = PedidoProduto.objects.get(id=pedido_produto_id, id_pedido=pedido)
                    item_to_delete.delete()
                    messages.success(request, "Produto removido do pedido.")
                    return redirect('editar_pedido', id=pedido.id)
                except PedidoProduto.DoesNotExist:
                    messages.error(request, "Produto não encontrado no pedido.")
                except Exception as e:
                    messages.error(request, f"Erro ao remover produto: {e}")
            else:
                messages.error(request, "ID do produto a ser removido não fornecido.")
        else:
            messages.warning(request, "Ação desconhecida.")

    item_formset = PedidoProdutoFormSet(instance=pedido)

    context = {
        'pedido': pedido,
        'item_formset': item_formset,
        'add_product_form': add_product_form,
    }
    return render(request, 'confeitaria/editar_pedido.html', context)


def deletar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)

    if request.method == "POST":
        pedido.delete()
        return redirect("listar_pedidos")          # volta para a lista

    # GET → exibe confirmação
    return render(request, "confeitaria/deletar_cliente.html", {"pedido": pedido})


def remover_produto_do_pedido(request, id_pedido_produto):
    # Pega o objeto PedidoProduto ou retorna 404 se não existir
    pedido_produto = get_object_or_404(PedidoProduto, id=id_pedido_produto)
    
    # Guarda o ID do pedido antes de deletar o item, para redirecionar corretamente
    id_do_pedido_associado = pedido_produto.id_pedido.id

    if request.method == 'POST':
        try:
            pedido_produto.delete()
            messages.success(request, "Produto removido do pedido com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao remover produto do pedido: {e}")
        
        # Redireciona de volta para a página de adicionar produtos ao pedido específico
        return redirect('adicionar_produto_ao_pedido', id_pedido=id_do_pedido_associado)
    
    messages.warning(request, "Método não permitido para remover o produto. Use o botão de remover.")
    return redirect('adicionar_produto_ao_pedido', id_pedido=id_do_pedido_associado)



def criar_usuario(request):
    if request.method == 'POST':
            form = UsuarioForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('autenticar_login')
    else:
        form = ProdutoForm()
    return render(request, 'confeitaria/cadastrar_usuario.html', {'form': form})

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

