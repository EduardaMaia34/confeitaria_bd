# confeitaria/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput
from .models import Produto, Cliente, Pedido, PedidoProduto, Usuario
from django.forms import inlineformset_factory

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
        widgets = {
            'quantidade': forms.NumberInput(attrs={'min': '1'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_produto'].queryset = Produto.objects.all()
        self.fields['id_produto'].empty_label = "--- Selecione um produto ---"
        self.fields['id_produto'].label = "Produto:"

PedidoProdutoFormSet = inlineformset_factory(
    Pedido,
    PedidoProduto,
    form=PedidoProdutoForm,
    extra=0,
    can_delete=True,
    fields=('id_produto', 'quantidade',)
)
    
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['usuario', 'senha']
