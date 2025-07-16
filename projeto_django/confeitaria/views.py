from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.contrib import messages
from .forms import ProdutoForm, ClienteForm, PedidoForm, PedidoProdutoForm, UsuarioForm, PedidoProdutoFormSet
from .models import Pedido, Cliente, Produto, PedidoProduto, Usuario
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse

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


def adicionar_produto_ao_pedido(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido)
    produtos = Produto.objects.all()
    itens_do_pedido = PedidoProduto.objects.filter(id_pedido=pedido)

    if request.method == 'POST':
        form = PedidoProdutoForm(request.POST)
        if form.is_valid():
            pedido_produto = form.save(commit=False)
            pedido_produto.id_pedido = pedido
            pedido_produto.save()
            messages.success(request, f"Produto '{pedido_produto.id_produto.nome}' adicionado com sucesso!")
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
        else:
            messages.error(request, "Erro ao adicionar produto. Verifique os dados.")
    else:
        form = PedidoProdutoForm()

    return render(request, 'confeitaria/adicionar_produto.html', {
        'pedido': pedido,
        'form': form,
        'produtos': produtos,
        'itens_do_pedido': itens_do_pedido
    })


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

    vendas = Pedido.objects.all().order_by('-data_pedido')

    if data_inicial and data_final:
        data_inicio = parse_date(data_inicial)
        data_fim = parse_date(data_final)

        if data_inicio and data_fim:
            vendas = vendas.filter(data_pedido__date__range=(data_inicio, data_fim))

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = vendas.count()

    total_itens = PedidoProduto.objects.filter(id_pedido__in=vendas).aggregate(
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

def criar_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            return redirect('adicionar_produto_ao_pedido', id_pedido=pedido.id)
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
                produto = add_product_form.cleaned_data['id_produto']
                quantidade = add_product_form.cleaned_data['quantidade']

                try:
                    existente = PedidoProduto.objects.get(id_pedido=pedido, id_produto=produto)
                    existente.quantidade += quantidade
                    existente.save()
                    messages.success(request, f"Quantidade do produto '{produto.nome}' atualizada.")
                except PedidoProduto.DoesNotExist:
                    novo = add_product_form.save(commit=False)
                    novo.id_pedido = pedido
                    novo.save()
                    messages.success(request, f"Produto '{novo.id_produto.nome}' adicionado.")

                return redirect('editar_pedido', id=pedido.id)
            else:
                messages.error(request, "Dados inválidos para adicionar produto.")

        elif 'save_existing_items' in request.POST:
            item_formset = PedidoProdutoFormSet(request.POST, instance=pedido)
            if item_formset.is_valid():
                item_formset.save()
                messages.success(request, "Produtos atualizados com sucesso!")
                return redirect('listar_pedidos')
            else:
                messages.error(request, "Erro ao salvar os produtos. Verifique os campos.")

        elif 'remove_item' in request.POST:
            pedido_produto_id = request.POST.get('pedido_produto_id')
            if pedido_produto_id:
                try:
                    item = PedidoProduto.objects.get(id=pedido_produto_id, id_pedido=pedido)
                    item.delete()
                    messages.success(request, "Produto removido do pedido.")
                    return redirect('editar_pedido', id=pedido.id)
                except PedidoProduto.DoesNotExist:
                    messages.error(request, "Produto não encontrado.")
                except Exception as e:
                    messages.error(request, f"Erro ao remover produto: {e}")
            else:
                messages.error(request, "ID do produto a ser removido não fornecido.")

    item_formset = PedidoProdutoFormSet(instance=pedido)

    return render(request, 'confeitaria/editar_pedido.html', {
        'pedido': pedido,
        'item_formset': item_formset,
        'add_product_form': add_product_form,
    })


def deletar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)

    if request.method == "POST":
        pedido.delete()
        return redirect("listar_pedidos")

    return render(request, "confeitaria/deletar_pedido.html", {"pedido": pedido})


def remover_produto_do_pedido(request, id_pedido_produto):
    pedido_produto = get_object_or_404(PedidoProduto, id=id_pedido_produto)
    id_do_pedido = pedido_produto.id_pedido.id

    if request.method == 'POST':
        try:
            pedido_produto.delete()
            messages.success(request, "Produto removido do pedido com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao remover produto: {e}")

        return redirect('adicionar_produto_ao_pedido', id_pedido=id_do_pedido)

    messages.warning(request, "Método inválido.")
    return redirect('adicionar_produto_ao_pedido', id_pedido=id_do_pedido)


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

    vendas = Pedido.objects.all().order_by('data_pedido')

    if data_inicial and data_final:
        try:
            data_inicio = parse_date(data_inicial)
            data_fim = parse_date(data_final)
            if data_inicio and data_fim:
                vendas = vendas.filter(data_pedido__date__range=[data_inicio, data_fim])
        except:
            vendas = Pedido.objects.none()

    total = vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_pedidos = vendas.count()

    total_itens = PedidoProduto.objects.filter(id_pedido__in=vendas).aggregate(
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