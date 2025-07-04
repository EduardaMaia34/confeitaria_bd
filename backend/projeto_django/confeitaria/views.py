from django.shortcuts import render, redirect
from .forms import ProdutoForm, ClienteForm

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
