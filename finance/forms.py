from decimal import Decimal

from django import forms

from .models import Transaction


class TransactionForm(forms.ModelForm):
    category = forms.CharField(strip=False)

    class Meta:
        model = Transaction
        fields = (
            'amount',
            'transaction_type',
            'category',
            'date',
            'description',
        )
        widgets = {
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= Decimal('0'):
            raise forms.ValidationError('Amount must be greater than 0.')
        return amount

    def clean_category(self):
        category = self.cleaned_data['category'].strip()
        if not category:
            raise forms.ValidationError('Category cannot be blank.')
        return category
