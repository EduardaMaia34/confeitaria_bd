# confeitaria/forms.py
from django import forms
from .models import Produto, Cliente, Pedido, PedidoProduto

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco']
        
    def __str__(self):
        return self.nome  # importante!
        
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'cpf']
    
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