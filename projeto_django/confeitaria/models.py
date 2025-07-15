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
    

class Pedido(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    data_pedido = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    forma_pagamento = models.CharField(max_length=50, choices=[
        ('dinheiro', 'Dinheiro'),
        ('pix', 'Pix'),
        ('debito', 'Cartão de Débito'),
        ('credito', 'Cartão de Crédito'),
    ])

class PedidoProduto(models.Model):
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length = 50)
    senha = models.CharField(max_length = 50)
    def __str__(self):
        return self.usuario