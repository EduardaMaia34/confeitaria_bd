from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection, transaction
import json
from decimal import Decimal
from datetime import datetime
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.utils import timezone


# Importa os modelos que estão faltando e o novo modelo da visão
from .models import Pedido, Produto, Cliente, PedidoConcluido, PedidoConcluidoProduto, VendaComCliente, PedidoProduto
from .forms import ProdutoForm, ClienteForm, UsuarioForm, PedidoProdutoForm, PedidoProdutoFormSet , PedidoForm


def is_gerente(user):
    return user.groups.filter(name='Gerentes').exists() or user.is_superuser or user.username == 'admin'


def menu(request):
    return render(request, 'confeitaria/menu.html')

@login_required
def menu_usuario(request):
    pedidos_pendentes = Pedido.objects.filter(modalidade='retirada').order_by('-data_pedido')
    
    total_pedidos = PedidoConcluido.objects.count()
    lucro_bruto = PedidoConcluido.objects.aggregate(Sum('valor_total'))['valor_total__sum']
    
    lucro_bruto_formatado = f"R$ {Decimal(lucro_bruto):.2f}".replace('.', ',') if lucro_bruto is not None else "R$ 0,00"

    context = {
        'pedidos_pendentes': pedidos_pendentes,
        'total_pedidos': total_pedidos,
        'lucro_bruto': lucro_bruto_formatado
    }

    return render(request, 'confeitaria/menu_usuario.html', context)


@login_required
def redirecionar_menu(request):
    """
    Redireciona o usuário para o menu apropriado após o login.
    """
    if is_gerente(request.user):
        return redirect('menu')
    else:
        return redirect('menu_usuario')



def autenticar_login(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user_input = request.POST.get('usuario')
            pwd_input = request.POST.get('senha')

            with connection.cursor() as cur:
                cur.execute("SELECT senha FROM confeitaria_usuario WHERE usuario = %s", [user_input])
                row = cur.fetchone()

            if row and pwd_input == row[0]:
                User = get_user_model()
                django_user, _ = User.objects.get_or_create(
                    username=user_input, defaults={"is_active": True}
                )
                django_login(request, django_user)
                
                return redirect('redirecionar_menu')

            messages.error(request, "Usuário ou senha incorretos.")
    else:
        form = UsuarioForm()

    return render(request, "confeitaria/login.html", {"form": form})


@login_required
def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar_produto')
    else:
        form = ProdutoForm()
    return render(request, 'confeitaria/cadastrar_produto.html', {'form': form})


@login_required
def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            telefone = form.cleaned_data['telefone']

            if Cliente.objects.filter(nome=nome, telefone=telefone).exists():
                messages.warning(request, "Cliente já existente.")
                return render(request, 'confeitaria/cadastrar_cliente.html', {'form': form})

            try:
                form.save()
                messages.success(request, "Cliente cadastrado com sucesso!")
                return redirect('listar_cliente')
            except Exception:
                messages.error(request, "Erro: não foi possível cadastrar o cliente.")
        else:
            messages.warning(request, "Dados inválidos. Verifique os campos.")
    else:
        form = ClienteForm()

    return render(request, 'confeitaria/cadastrar_cliente.html', {'form': form})

@login_required
def criar_pedido(request):
    clientes = Cliente.objects.all().order_by('nome')
    produtos = Produto.objects.all().order_by('nome')

    if request.method == 'POST':
        try:
            dados_json = json.loads(request.body)
            
            cliente_id = dados_json.get('cliente')
            modalidade = dados_json.get('modalidade')
            data_retirada_str = dados_json.get('data_retirada')
            forma_pagamento = dados_json.get('forma_pagamento')
            observacoes = dados_json.get('observacoes', '')
            itens_pedido_json = dados_json.get('pedido_items', [])

            if not itens_pedido_json:
                return JsonResponse({'success': False, 'error': 'Pelo menos um item é obrigatório.'}, status=400)

            data_retirada = None
            if data_retirada_str:
                data_retirada = datetime.strptime(data_retirada_str, '%Y-%m-%d').date()

            with transaction.atomic():
                cliente = None
                if cliente_id:
                    cliente = Cliente.objects.get(pk=cliente_id)

                pedido = Pedido.objects.create(
                    cliente=cliente,
                    modalidade=modalidade,
                    data_retirada=data_retirada,
                    data_pedido=timezone.now(),
                    forma_pagamento=forma_pagamento,
                    observacoes=observacoes,
                    em_preparo=True
                )

                total = Decimal('0.00')
                for item_data in itens_pedido_json:
                    produto = Produto.objects.get(pk=item_data['id'])
                    quantidade = item_data['quantidade']
                    
                    total += produto.preco * quantidade
                    
                    PedidoProduto.objects.create(
                        id_pedido=pedido,
                        id_produto=produto,
                        quantidade=quantidade
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
            return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'}, status=500)

    context = {
        'clientes': clientes,
        'produtos': produtos
    }
    return render(request, 'confeitaria/cadastrar_pedido.html', context)

@login_required
def editar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # Passo 1: Buscamos todos os produtos e preparamos os dados para o JavaScript
    # Passamos os dados como um objeto Python, sem json.dumps()
    produtos_data = list(Produto.objects.all().order_by('nome').values('id', 'nome'))

    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        formset = PedidoProdutoFormSet(request.POST, request.FILES, instance=pedido)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            
            for item in formset.save(commit=False):
                if item.id:
                    item.save()
                else:
                    item.id_pedido = pedido
                    item.save()
            
            for item in formset.deleted_objects:
                item.delete()

            novo_valor_total = Decimal('0.00')
            for item in pedido.itens_do_pedido.all():
                novo_valor_total += item.id_produto.preco * item.quantidade

            if pedido.cliente:
                novo_valor_total *= Decimal('0.90')
            
            pedido.valor_total = novo_valor_total
            pedido.save()

            return JsonResponse({'success': True, 'redirect_url': '/listar_pedidos/'})
        else:
            contexto = {
                'pedido': pedido,
                'form': form,
                'formset': formset,
                'produtos_data': produtos_data, # Passa o objeto Python
            }
            html = render_to_string('confeitaria/partials/modal_editar_pedido.html', contexto, request=request)
            return JsonResponse({'success': False, 'form_html': html})

    else:
        form = PedidoForm(instance=pedido)
        formset = PedidoProdutoFormSet(instance=pedido)

    contexto = {
        'pedido': pedido,
        'form': form,
        'formset': formset,
        # Passo 2: Passamos o objeto Python
        'produtos_data': produtos_data,
    }

    return render(request, 'confeitaria/partials/modal_editar_pedido.html', contexto)

@login_required
def marcar_pronto(request, pedido_id):
    if request.method == 'POST':
        try:
            pedido = get_object_or_404(Pedido, pk=pedido_id)
            pedido.em_preparo = False
            pedido.save()
            return JsonResponse({'success': True})
        except Pedido.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)


@login_required
def listar_pedidos(request):
    pedidos = Pedido.objects.all().order_by('data_pedido'). prefetch_related('itens_do_pedido__id_produto')
    produtos = list(Produto.objects.values('id', 'nome'))
    
    context = {
        'pedidos': pedidos,
        'produtos': produtos  # Isso resolve o problema de dados ausentes
    }
    
    return render(request, 'confeitaria/lista_pedidos.html', context)


@login_required
def confirmar_pagamento(request, pedido_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                pedido = get_object_or_404(Pedido, pk=pedido_id)

                valor_total_calculado = Decimal('0.00')
                for item in pedido.itens_do_pedido.all():
                    valor_total_calculado += item.id_produto.preco * item.quantidade

                if pedido.cliente:
                    valor_total_calculado *= Decimal('0.90')

                pedido_concluido = PedidoConcluido.objects.create(
                    id_original=pedido.id,
                    cliente=pedido.cliente,
                    data_pedido=pedido.data_pedido,
                    modalidade=pedido.modalidade,
                    data_retirada=pedido.data_retirada,
                    forma_pagamento=pedido.forma_pagamento,
                    observacoes=pedido.observacoes,
                    valor_total=valor_total_calculado
                )

                for item in pedido.itens_do_pedido.all():
                    PedidoConcluidoProduto.objects.create(
                        id_pedido_concluido=pedido_concluido,
                        id_produto=item.id_produto,
                        quantidade=item.quantidade
                    )
                
                pedido.delete()
                
                total_pedidos = PedidoConcluido.objects.count()
                lucro_bruto = PedidoConcluido.objects.aggregate(Sum('valor_total'))['valor_total__sum'] or Decimal('0.00')

                return JsonResponse({
                    'success': True,
                    'lucro_bruto': f"R$ {lucro_bruto:.2f}".replace('.', ','),
                    'total_pedidos': total_pedidos
                })

        except Pedido.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)


@login_required
def cancelar_pedido(request, pedido_id):
    try:
        pedido = get_object_or_404(Pedido, pk=pedido_id)
        pedido.delete()
        return JsonResponse({'success': True, 'message': 'Pedido cancelado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
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

    usuario_eh_gerente = is_gerente(request.user)

    context = {
        'produtos': produtos,
        'is_gerente': usuario_eh_gerente,
        'search_query': search_query,
    }

    return render(request, 'confeitaria/interface_produto.html', context)


@login_required
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


@login_required
def editar_produto_modal(request, id):
    produto = get_object_or_404(Produto, id=id)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            html = render_to_string('confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto}, request=request)
            return JsonResponse({'success': False, 'form_html': html})
    else:
        form = ProdutoForm(instance=produto)

    return render(request, 'confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto})


@login_required
def deletar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)

    if request.method == "POST":
        produto.delete()
        return redirect("listar_produto")

    return render(request, "confeitaria/deletar_produto.html", {"produto": produto})


@login_required
def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('listar_cliente')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'confeitaria/editar_cliente.html', {'form': form, 'cliente': cliente})


@login_required
def deletar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == "POST":
        cliente.delete()
        return redirect("listar_cliente")

    return render(request, "confeitaria/deletar_cliente.html", {"cliente": cliente})


@login_required
def relatorio_vendas(request):
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')
    
    sql_query = """
    SELECT
        T1.*,
        T2.nome AS cliente__nome, 
        T2.telefone AS cliente__telefone
    FROM
        confeitaria_pedidoconcluido AS T1
    LEFT JOIN
        confeitaria_cliente AS T2
    ON
        T1.cliente_id = T2.id
    """
    
    params = []
    
    if data_inicial and data_final:
        data_inicio = parse_date(data_inicial)
        data_fim = parse_date(data_final)
        
        if data_inicio and data_fim:
            sql_query += " WHERE T1.data_pedido::date BETWEEN %s AND %s"
            params.extend([data_inicio, data_fim])

    sql_query += " ORDER BY T1.data_pedido DESC"

    vendas = PedidoConcluido.objects.raw(sql_query, params)

    total = sum(venda.valor_total for venda in vendas) if vendas else 0
    total_pedidos = len(list(vendas))

    venda_ids = [venda.id for venda in vendas]
    total_itens = PedidoConcluidoProduto.objects.filter(
        id_pedido_concluido__in=venda_ids
    ).aggregate(total=Sum('quantidade'))['total'] or 0

    ticket_medio = round(total / total_pedidos, 2) if total_pedidos else 0

    context = {
        'vendas': vendas,
        'total': total,
        'total_pedidos': total_pedidos,
        'total_itens': total_itens,
        'ticket_medio': ticket_medio,
    }

    return render(request, 'confeitaria/relatorio_vendas.html', context)


def criar_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('autenticar_login')
    else:
        form = UsuarioForm()

    return render(request, 'confeitaria/cadastrar_usuario.html', {'form': form})


@login_required
def gerar_pdf_relatorio_vendas(request):
    
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    vendas = VendaComCliente.objects.all().order_by('-data_pedido')

    if data_inicial and data_final:
        try:
            data_inicio = parse_date(data_inicial)
            data_fim = parse_date(data_final)
            if data_inicio and data_fim:
                vendas = vendas.filter(data_pedido__date__range=[data_inicio, data_fim])
        except:
            vendas = VendaComCliente.objects.none()

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = vendas.count()

    venda_ids = [venda.id for venda in vendas]
    total_itens = PedidoConcluidoProduto.objects.filter(id_pedido_concluido__in=venda_ids).aggregate(
        total=Sum('quantidade')
    )['total'] or 0

    ticket_medio = round(total / total_pedidos, 2) if total_pedidos else 0

    context = {
        'vendas': vendas,
        'data_inicial': datetime.strptime(data_inicial, "%Y-%m-%d").strftime("%d/%m/%Y") if data_inicial else "",
        'data_final': datetime.strptime(data_final, "%Y-%m-%d").strftime("%d/%m/%Y") if data_final else "",
        'total': f"{total:.2f}",
        'total_itens': total_itens,
        'ticket_medio': f"{ticket_medio:.2f}",
        'data_atual': now()
    }

    template = get_template('confeitaria/pdf_relatorio_vendas.html')
    html = template.render(context)

    response = BytesIO()
    pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=response, encoding='utf-8')

    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)

    response.seek(0)
    return HttpResponse(response, content_type='application/pdf')



def render_formulario_edicao(request, pedido):
    """Renderiza o formulário HTML para edição do pedido"""
    try:
        itens_pedido = PedidoProduto.objects.filter(
            id_pedido=pedido
        ).select_related('id_produto')
        
        produtos = Produto.objects.filter(ativo=True).order_by('nome')
        clientes = Cliente.objects.filter(ativo=True).order_by('nome')

        context = {
            'pedido': pedido,
            'itens_pedido': itens_pedido,
            'produtos': produtos,
            'clientes': clientes,
            'modalidades': dict(Pedido.MODALIDADE_CHOICES),
            'formas_pagamento': dict(Pedido.FORMA_PAGAMENTO_CHOICES),
            'STATUS_PEDIDO': dict(Pedido.STATUS_CHOICES),
        }
        
        return render(
            request,
            'confeitaria/partials/modal_editar_pedido.html',
            context
        )
        
    except Exception as e:
        print(f"Erro ao renderizar formulário: {str(e)}")
        return render(
            request,
            'confeitaria/partials/modal_erro.html',
            {'mensagem': 'Erro ao carregar formulário de edição'},
            status=500
        )

def processar_edicao_pedido(request, pedido):
    """Processa as alterações do pedido via AJAX"""
    try:
        dados = json.loads(request.body)
        
        # Validação básica dos dados
        if not validar_dados_pedido(dados):
            return JsonResponse({
                'success': False,
                'error': 'Dados do pedido inválidos'
            }, status=400)

        with transaction.atomic():
            # Atualiza os dados principais do pedido
            atualizar_dados_principais(pedido, dados)
            
            # Processa os itens do pedido
            valor_total = processar_itens_pedido(pedido, dados.get('itens', []))
            
            # Atualiza valor total e salva
            pedido.valor_total = valor_total
            pedido.save()

        return JsonResponse({
            'success': True,
            'pedido_id': pedido.id,
            'valor_total': f"R$ {pedido.valor_total:.2f}",
            'status': pedido.get_status_display(),
            'status_class': pedido.status
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dados JSON inválidos'
        }, status=400)
        
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente não encontrado'
        }, status=404)
        
    except Produto.DoesNotExist as e:
        return JsonResponse({
            'success': False,
            'error': f'Produto não encontrado: {str(e)}'
        }, status=404)
        
    except Exception as e:
        print(f"Erro ao editar pedido: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)

def validar_dados_pedido(dados):
    """Valida os dados recebidos do pedido"""
    if not dados.get('itens'):
        return False
        
    if dados.get('modalidade') not in dict(Pedido.MODALIDADE_CHOICES):
        return False
        
    if dados.get('forma_pagamento') not in dict(Pedido.FORMA_PAGAMENTO_CHOICES):
        return False
        
    return True

def atualizar_dados_principais(pedido, dados):
    """Atualiza os dados principais do pedido"""
    pedido.cliente_id = dados.get('cliente_id')
    pedido.modalidade = dados.get('modalidade')
    pedido.forma_pagamento = dados.get('forma_pagamento')
    pedido.observacoes = dados.get('observacoes', '')[:500]  # Limita a 500 caracteres
    
    # Converte a data de retirada se existir
    if dados.get('data_retirada'):
        try:
            pedido.data_retirada = datetime.strptime(
                dados['data_retirada'],
                '%Y-%m-%d'
            ).date()
        except (ValueError, TypeError):
            pedido.data_retirada = None

def processar_itens_pedido(pedido, itens):
    """Processa e atualiza os itens do pedido, retorna o valor total"""
    # Remove itens antigos
    PedidoProduto.objects.filter(id_pedido=pedido).delete()
    
    total = Decimal('0.00')
    
    for item in itens:
        produto = Produto.objects.get(
            pk=item['produto_id'],
            ativo=True
        )
        
        quantidade = int(item['quantidade'])
        if quantidade <= 0:
            continue  # Ignora quantidades inválidas
            
        PedidoProduto.objects.create(
            id_pedido=pedido,
            id_produto=produto,
            quantidade=quantidade,
            preco_unitario=produto.preco
        )
        
        total += produto.preco * quantidade
    
    # Aplica desconto para clientes cadastrados
    if pedido.cliente_id:
        total *= Decimal('0.90')  # 10% de desconto
        
    return total

def api_pedido_detalhe(request, pedido_id):
    try:
        pedido = Pedido.objects.get(id=pedido_id)
        
        # Use select_related para buscar o produto em uma única consulta, melhorando a performance
        itens = PedidoProduto.objects.filter(id_pedido=pedido).select_related('id_produto')

        itens_list = []
        for item in itens:
            # Calcule o subtotal aqui na view
            subtotal_item = item.quantidade * item.id_produto.preco
            
            itens_list.append({
                'id': item.id,
                'produto_id': item.id_produto.id,
                'nome_produto': item.id_produto.nome,
                'quantidade': item.quantidade,
                'preco_unitario': float(item.id_produto.preco),
                'subtotal': float(subtotal_item), # Use a variável calculada
            })

        pedido_data = {
            'id': pedido.id,
            'cliente': pedido.cliente.nome if pedido.cliente else 'N/A',
            'data_pedido': pedido.data_pedido.isoformat(),
            'valor_total': float(pedido.valor_total),
            'modalidade': pedido.get_modalidade_display(),
            'forma_pagamento': pedido.get_forma_pagamento_display(),
            'em_preparo': pedido.em_preparo,
            'observacoes': pedido.observacoes,
            'data_retirada': pedido.data_retirada.isoformat() if pedido.data_retirada else None,
        }

        return JsonResponse({'pedido': pedido_data, 'itens': itens_list})

    except Pedido.DoesNotExist:
        return JsonResponse({'error': 'Pedido não encontrado.'}, status=404)