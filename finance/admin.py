from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'amount',
        'transaction_type',
        'category',
        'date',
        'description',
    )