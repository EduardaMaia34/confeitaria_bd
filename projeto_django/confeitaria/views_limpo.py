from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as django_login, get_user_model
from django.db import connection, transaction
import json
from decimal import Decimal
from datetime import datetime
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

# Importa os modelos que estão faltando e o novo modelo da visão
from .models import Pedido, Produto, Cliente, PedidoConcluido, PedidoConcluidoProduto, VendaComCliente, PedidoProduto
from .forms import ProdutoForm, ClienteForm, UsuarioForm, PedidoProdutoForm, PedidoProdutoFormSet   
