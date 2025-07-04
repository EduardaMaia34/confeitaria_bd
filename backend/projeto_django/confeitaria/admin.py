from django.contrib import admin

# Register your models here.
# confeitaria/admin.py
from .models import Produto

admin.site.register(Produto)
