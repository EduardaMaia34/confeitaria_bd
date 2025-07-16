from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm, UsuarioForm
from .models import Pedido, PedidoConcluido, Cliente, Produto, PedidoProduto, Usuario, PedidoConcluidoProduto
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection
import json
from decimal import Decimal
from datetime import datetime


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
    clientes = Cliente.objects.all()
    produtos = Produto.objects.all()
    
    if request.method == 'POST':
        try:
            dados_json = json.loads(request.body)
            
            cliente_id = dados_json.get('cliente')
            modalidade = dados_json.get('modalidade')
            # Lendo a data como string do JSON
            data_retirada_str = dados_json.get('data_retirada')
            forma_pagamento = dados_json.get('forma_pagamento')
            observacoes = dados_json.get('observacoes')
            em_preparo = True
            itens_pedido = dados_json.get('pedido_items', [])

            if not itens_pedido:
                return JsonResponse({'success': False, 'error': 'Pelo menos um item é obrigatório.'}, status=400)

            # === INÍCIO DA LÓGICA MODIFICADA PARA A DATA ===
            data_retirada = None # Define o valor inicial como None (nulo)
            if data_retirada_str: # Se a string da data não estiver vazia
                try:
                    # Converte a string para um objeto datetime.date
                    data_retirada = datetime.strptime(data_retirada_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Formato de data de retirada inválido. Use YYYY-MM-DD.'}, status=400)
            # === FIM DA LÓGICA MODIFICADA ===

            with transaction.atomic():
                cliente = Cliente.objects.get(pk=cliente_id) if cliente_id else None

                pedido = Pedido.objects.create(
                    cliente=cliente,
                    modalidade=modalidade,
                    data_retirada=data_retirada, # Usa a variável já tratada
                    forma_pagamento=forma_pagamento,
                    observacoes=observacoes,
                    em_preparo=em_preparo
                )

                total = Decimal('0.00')
                for item in itens_pedido:
                    produto = Produto.objects.get(pk=item['id'])
                    subtotal = produto.preco * item['quantidade']
                    total += subtotal

                    # Verifique o nome do seu modelo de item de pedido.
                    # Se for PedidoProduto, mantenha como está.
                    PedidoProduto.objects.create(
                        id_pedido=pedido,
                        id_produto=produto,
                        quantidade=item['quantidade']
                    )

                if cliente:
                    total *= Decimal('0.90')

                pedido.valor_total = total
                pedido.save()

            return JsonResponse({'success': True, 'pedido_id': pedido.id})

        except Cliente.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cliente não encontrado.'}, status=404)
        except Produto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Produto não encontrado.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Dados JSON inválidos.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
    context = {
        'clientes': clientes,
        'produtos': produtos
    }
    return render(request, 'confeitaria/cadastrar_pedido.html', context)

def marcar_pronto(request, pedido_id):
    if request.method == 'POST':
        try:
            pedido = get_object_or_404(Pedido, pk=pedido_id)
            pedido.em_preparo = False
            pedido.pago = False
            pedido.save()
            return JsonResponse({'success': True})
        except Pedido.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)



def listar_pedidos(request):
    # Busca todos os pedidos, sem nenhum filtro
    pedidos = Pedido.objects.all().order_by('data_pedido')
    context = {
        'pedidos': pedidos
    }
    return render(request, 'confeitaria/lista_pedidos.html', context)

def confirmar_pagamento(request, pedido_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Busca o pedido original
                pedido = get_object_or_404(Pedido, pk=pedido_id)

                # 2. Cria o registro na tabela de pedidos concluídos, copiando os dados
                pedido_concluido = PedidoConcluido.objects.create(
                    id_original=pedido.id,
                    cliente=pedido.cliente,
                    data_pedido=pedido.data_pedido,
                    modalidade=pedido.modalidade,
                    data_retirada=pedido.data_retirada,
                    forma_pagamento=pedido.forma_pagamento,
                    observacoes=pedido.observacoes
                )

                # 3. Copia os itens do pedido para a nova tabela de produtos concluídos
                for item in pedido.pedidoproduto_set.all():
                    PedidoConcluidoProduto.objects.create(
                        id_pedido_concluido=pedido_concluido,
                        id_produto=item.id_produto,
                        quantidade=item.quantidade
                    )

                # 4. Exclui o pedido original
                pedido.delete()
            
            return JsonResponse({'success': True})

        except Pedido.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)

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