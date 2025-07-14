# confeitaria/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput
from .models import Produto, Cliente, Pedido, PedidoProduto, Usuario

class CustomClearableFileInput(ClearableFileInput):
    # Definindo template_name como um atributo da classe
    template_name = 'widgets/custom_clearable_file_input.html'

# Form do Produto
class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'imagem']
        widgets = {
            # Agora, instancie o seu widget personalizado sem passar template_name aqui
            'imagem': CustomClearableFileInput(attrs={'class': 'meu-input-imagem'}),
        }    
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garante que o campo seja um select com os produtos
        self.fields['id_produto'].queryset = Produto.objects.all()
    
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['usuario', 'senha']
        