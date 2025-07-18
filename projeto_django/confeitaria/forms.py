# confeitaria/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput, DateInput
from django.forms import inlineformset_factory
from .models import Produto, Cliente, Pedido, PedidoProduto, Usuario

# Custom Widget
class CustomClearableFileInput(ClearableFileInput):
    template_name = 'widgets/custom_clearable_file_input.html'

# Form do Produto
class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-textarea'}),
            'preco': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'telefone', 'rua', 'numero', 'bairro', 'cep']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'rua': forms.TextInput(attrs={'class': 'form-input'}),
            'numero': forms.TextInput(attrs={'class': 'form-input'}),
            'bairro': forms.TextInput(attrs={'class': 'form-input'}),
            'cep': forms.TextInput(attrs={'class': 'form-input'}),
        }

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = '__all__'

class PedidoProdutoForm(forms.ModelForm):
    id_produto = forms.ModelChoiceField(
        queryset=Produto.objects.all().order_by('nome'),
        label="Produto",
        empty_label="Selecione um produto"
    )
    
    class Meta:
        model = PedidoProduto
        fields = ['id_produto', 'quantidade']

# Esta é a definição mais importante. Garanta que ela esteja exatamente assim.
PedidoProdutoFormSet = inlineformset_factory(
    Pedido,
    PedidoProduto,
    form=PedidoProdutoForm, # <--- ADICIONE ESTA LINHA
    extra=1,
    can_delete=True
)


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['usuario', 'senha']