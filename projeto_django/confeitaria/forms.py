# confeitaria/forms.py
from django import forms
from .models import Produto, Cliente, Pedido, PedidoProduto, Usuario

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'imagem']
        
    def __str__(self):
        return self.nome  # importante!
        
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'telefone', 'rua', 'numero', 'bairro', 'cep']
    
    def __str__(self):
        return self.nome

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cliente']  # data_pedido é automático
    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente.nome} - {self.data_pedido.strftime('%d/%m/%Y %H:%M')}"

class PedidoProdutoForm(forms.ModelForm):
    class Meta:
        model = PedidoProduto
        fields = ['id_produto', 'quantidade']
    
    def __str__(self):
        return f"{self.produto.nome} (Qtd: {self.quantidade})"
    
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['usuario', 'senha']
        