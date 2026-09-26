from django.db import models
from django.contrib.auth.models import User


class Transaction(models.Model):

    user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    null=True,
    blank=True
    )

    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )
    category = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"