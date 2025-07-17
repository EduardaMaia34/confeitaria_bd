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

# Importa os modelos que estão faltando
from .models import Pedido, Produto, Cliente, PedidoProduto, PedidoConcluido, PedidoConcluidoProduto
from .forms import ProdutoForm, ClienteForm, UsuarioForm


def is_gerente(user):
    return user.groups.filter(name='Gerentes').exists() or user.is_superuser or user.username == 'admin'


def menu(request):
    return render(request, 'confeitaria/menu.html')


def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar_produto')
    else:
        form = ProdutoForm()
    return render(request, 'confeitaria/cadastrar_produto.html', {'form': form})


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


def criar_pedido(request):
    clientes = Cliente.objects.all().order_by('nome')
    produtos = Produto.objects.all().order_by('nome')

    if request.method == 'POST':
        try:
            # Carrega o JSON da requisição
            dados_json = json.loads(request.body)
            
            # Extrai os dados
            cliente_id = dados_json.get('cliente')
            modalidade = dados_json.get('modalidade')
            data_retirada_str = dados_json.get('data_retirada')
            forma_pagamento = dados_json.get('forma_pagamento')
            observacoes = dados_json.get('observacoes', '')
            itens_pedido_json = dados_json.get('pedido_items', [])

            if not itens_pedido_json:
                return JsonResponse({'success': False, 'error': 'Pelo menos um item é obrigatório.'}, status=400)

            # Converte a string da data para um objeto date
            data_retirada = None
            if data_retirada_str:
                data_retirada = datetime.strptime(data_retirada_str, '%Y-%m-%d').date()

            with transaction.atomic():
                # Encontra o cliente se o ID foi fornecido
                cliente = None
                if cliente_id:
                    cliente = Cliente.objects.get(pk=cliente_id)

                # Cria o objeto Pedido
                pedido = Pedido.objects.create(
                    cliente=cliente,
                    modalidade=modalidade,
                    data_retirada=data_retirada,
                    data_pedido=timezone.now(),
                    forma_pagamento=forma_pagamento,
                    observacoes=observacoes,
                    em_preparo=True # Pedidos novos sempre começam "em preparo"
                )

                total = Decimal('0.00')
                for item_data in itens_pedido_json:
                    produto = Produto.objects.get(pk=item_data['id'])
                    quantidade = item_data['quantidade']
                    
                    total += produto.preco * quantidade
                    
                    # Cria o relacionamento PedidoProduto
                    PedidoProduto.objects.create(
                        id_pedido=pedido,
                        id_produto=produto,
                        quantidade=quantidade
                    )
                    
                    total += produto.preco * quantidade
                
                # Aplica o desconto se for cliente VIP
                if cliente and cliente.tipo == 'cliente_vip':
                    total *= Decimal('0.90')

                # Atualiza o valor total do pedido
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
            # Captura a exceção e retorna a mensagem de erro detalhada
            return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'}, status=500)

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
            pedido.save()
            return JsonResponse({'success': True})
        except Pedido.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pedido não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)


def listar_pedidos(request):
    pedidos = Pedido.objects.all().order_by('data_pedido')
    context = {
        'pedidos': pedidos
    }
    return render(request, 'confeitaria/lista_pedidos.html', context)

def confirmar_pagamento(request, pedido_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                pedido = get_object_or_404(Pedido, pk=pedido_id)

                # 1. Calcula o valor total uma única vez
                valor_total_calculado = Decimal('0.00')
                for item in pedido.itens_do_pedido.all():
                    valor_total_calculado += item.id_produto.preco * item.quantidade

                # 2. Aplica o desconto de 10% se o pedido tiver um cliente associado
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
                return redirect("menu_usuario")

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

    usuario_eh_gerente = is_gerente(request.user)

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
            html = render_to_string('confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto}, request=request)
            return JsonResponse({'success': False, 'form_html': html})
    else:
        form = ProdutoForm(instance=produto)

    return render(request, 'confeitaria/partials/produto_form_partial.html', {'form': form, 'produto': produto})


def deletar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)

    if request.method == "POST":
        produto.delete()
        return redirect("listar_produto")

    return render(request, "confeitaria/deletar_produto.html", {"produto": produto})


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


def deletar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == "POST":
        cliente.delete()
        return redirect("listar_cliente")

    return render(request, "confeitaria/deletar_cliente.html", {"cliente": cliente})

def relatorio_vendas(request):
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    vendas = PedidoConcluido.objects.all().order_by('-data_pedido')

    if data_inicial and data_final:
        data_inicio = parse_date(data_inicial)
        data_fim = parse_date(data_final)

        if data_inicio and data_fim:
            vendas = vendas.filter(data_pedido__date__range=(data_inicio, data_fim))

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = vendas.count()

    total_itens = PedidoConcluidoProduto.objects.filter(id_pedido_concluido__in=vendas).aggregate(
        total=Sum('quantidade')
    )['total'] or 0

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

def gerar_pdf_relatorio_vendas(request):
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    vendas = PedidoConcluido.objects.all().order_by('data_pedido')

    if data_inicial and data_final:
        try:
            data_inicio = parse_date(data_inicial)
            data_fim = parse_date(data_final)
            if data_inicio and data_fim:
                vendas = vendas.filter(data_pedido__date__range=[data_inicio, data_fim])
        except:
            vendas = PedidoConcluido.objects.none()

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = vendas.count()

    total_itens = PedidoConcluidoProduto.objects.filter(id_pedido_concluido__in=vendas).aggregate(
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
        'agora': now()
    }

    template = get_template('confeitaria/pdf_relatorio_vendas.html')
    html = template.render(context)

    response = BytesIO()
    pisa_status = pisa.CreatePDF(html.encode('utf-8'), dest=response, encoding='utf-8')

    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)

    response.seek(0)
    return HttpResponse(response, content_type='application/pdf')


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