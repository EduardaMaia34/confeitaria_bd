from django.db import models

class Produto(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=6, decimal_places=2)
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
        return f"Pedido #{self.id} - {self.cliente.nome}"
    
    def update_valor_total(self):
        total = self.itens_do_pedido.aggregate(
            total_sum=Sum(F('quantidade') * F('id_produto__preco'))
        )['total_sum']
        
        self.valor_total = total if total is not None else 0.00
        self.save(update_fields=['valor_total'])


class PedidoProduto(models.Model):
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

class PedidoConcluido(models.Model):
    id_original = models.IntegerField(unique=True) 
    cliente = models.ForeignKey('Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    data_pedido = models.DateTimeField()
    modalidade = models.CharField(max_length=20, choices=Pedido.MODALIDADE_CHOICES)
    data_retirada = models.DateTimeField(null=True, blank=True)
    forma_pagamento = models.CharField(max_length=20, choices=Pedido.FORMA_PAGAMENTO_CHOICES)
    observacoes = models.TextField(blank=True, null=True)
    data_confirmacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido Concluído #{self.id_original}"

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