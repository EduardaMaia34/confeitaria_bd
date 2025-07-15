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
    

class Pedido(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    data_pedido = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Pedido #{self.id} - Cliente: {self.cliente.nome}"

    def update_valor_total(self):
        total = self.itens_do_pedido.aggregate(
            total_sum=Sum(F('quantidade') * F('id_produto__preco'))
        )['total_sum']
        
        self.valor_total = total if total is not None else 0.00
        self.save(update_fields=['valor_total'])


class PedidoProduto(models.Model):
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens_do_pedido')
    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ('id_pedido', 'id_produto')
    
    def __str__(self):
        return f"{self.quantidade} x {self.id_produto.nome} no Pedido #{self.id_pedido.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.id_pedido.update_valor_total()

@receiver(post_delete, sender=PedidoProduto)
def update_pedido_total_on_delete(sender, instance, **kwargs):
    instance.id_pedido.update_valor_total()

class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length = 50)
    senha = models.CharField(max_length = 50)
    def __str__(self):
        return self.usuario