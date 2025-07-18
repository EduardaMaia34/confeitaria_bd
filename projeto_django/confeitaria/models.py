from django.db import models
from django.db.models import Sum, F
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Produto(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    
    def __str__(self):
        return self.nome


class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15, default='')  # Formato: (00) 00000-0000
    rua = models.CharField(max_length=100, default='')
    numero = models.CharField(max_length=10, default='')
    bairro = models.CharField(max_length=50, default='')
    cep = models.CharField(max_length=9, default='')  # Formato: 00000-000

    def __str__(self):
        return self.nome


from django.db import models

class Pedido(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey('Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    data_pedido = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    MODALIDADE_CHOICES = [
        ('loja', 'Consumo na Loja'),
        ('retirada', 'Retirada'),
    ]
    modalidade = models.CharField(max_length=20, choices=MODALIDADE_CHOICES, default='loja')
    data_retirada = models.DateTimeField(null=True, blank=True)
    FORMA_PAGAMENTO_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('cartao', 'Cartão'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
    ]
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, default='dinheiro')
    em_preparo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)

   
    def __str__(self):
        if self.cliente:
            return f"Pedido #{self.id} - {self.cliente.nome}"
        return f"Pedido #{self.id} - Sem cliente"


class PedidoProduto(models.Model):
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens_do_pedido')
    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)


class PedidoConcluido(models.Model):
    id = models.AutoField(primary_key=True)
    id_original = models.IntegerField(null=True, blank=True)
    cliente = models.ForeignKey('Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    data_pedido = models.DateTimeField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Adicione esta linha
    modalidade = models.CharField(max_length=20, default='loja')
    data_retirada = models.DateTimeField(null=True, blank=True)
    forma_pagamento = models.CharField(max_length=20, default='dinheiro')
    observacoes = models.TextField(blank=True, null=True)
    data_confirmacao = models.DateTimeField(auto_now_add=True) # Data em que o pedido foi concluído

    def __str__(self):
        return f"Pedido Concluido #{self.id}"
    
class PedidoConcluidoProduto(models.Model):
    id_pedido_concluido = models.ForeignKey(PedidoConcluido, on_delete=models.CASCADE)
    id_produto = models.ForeignKey('Produto', on_delete=models.SET_NULL, null=True)
    quantidade = models.IntegerField()
    
    def __str__(self):
        return f"{self.quantidade}x {self.id_produto.nome}"


class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length = 50)
    senha = models.CharField(max_length = 50)
    def __str__(self):
        return self.usuario
    
class VendaComCliente(models.Model):
    # Campos da sua view, com o nome que você definiu no SQL
    id = models.IntegerField(primary_key=True)
    data_pedido = models.DateTimeField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    modalidade = models.CharField(max_length=50)
    data_retirada = models.DateField(null=True, blank=True)
    forma_pagamento = models.CharField(max_length=50)
    observacoes = models.TextField(blank=True, null=True)
    cliente_id = models.IntegerField(null=True, blank=True)
    id_original = models.IntegerField()
    cliente_nome = models.CharField(max_length=100, null=True)
    cliente_telefone = models.CharField(max_length=15, null=True)

    class Meta:
        managed = False
        db_table = 'confeitaria_vendas_com_clientes'