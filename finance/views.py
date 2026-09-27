from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TransactionForm
from .models import Transaction


def _transaction_queryset(request, transaction_filter, search_query):
    transaction_query = Q(user=request.user)
    if transaction_filter != 'all':
        transaction_query &= Q(transaction_type=transaction_filter)
    if search_query:
        transaction_query &= (
            Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(transaction_type__icontains=search_query)
        )
    return Transaction.objects.filter(transaction_query).order_by(
        '-date',
        '-created_at',
        '-pk',
    )


@login_required
def dashboard(request):
    total_income = Transaction.objects.filter(
        user=request.user,
        transaction_type='income'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_expenses = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    balance = total_income - total_expenses

    transaction_filter = request.GET.get('type', 'all')
    if transaction_filter not in {'all', 'income', 'expense'}:
        transaction_filter = 'all'

    search_query = request.GET.get('search', '').strip()

    user_transactions = Transaction.objects.filter(user=request.user)
    transactions = _transaction_queryset(
        request,
        transaction_filter,
        search_query,
    )[:5]
    expense_categories = list(
        user_transactions.filter(transaction_type='expense')
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'income_expense_totals': [float(total_income), float(total_expenses)],
        'transactions': transactions,
        'transaction_filter': transaction_filter,
        'search_query': search_query,
        'expense_categories': [
            {'category': item['category'], 'total': float(item['total'])}
            for item in expense_categories
        ],
    }

    return render(request, 'finance/dashboard.html', context)


@login_required
def all_transactions(request):
    transaction_filter = request.GET.get('type', 'all')
    if transaction_filter not in {'all', 'income', 'expense'}:
        transaction_filter = 'all'

    search_query = request.GET.get('search', '').strip()
    paginator = Paginator(
        _transaction_queryset(request, transaction_filter, search_query),
        10,
    )
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'finance/all_transactions.html',
        {
            'page_obj': page_obj,
            'transaction_filter': transaction_filter,
            'search_query': search_query,
        },
    )

@login_required
def add_transaction(request):
    form = TransactionForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('dashboard')

    return render(request, 'finance/add_transaction.html', {'form': form})

@login_required
def edit_transaction(request, transaction_id):
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        user=request.user
    )

    form = TransactionForm(
        request.POST if request.method == 'POST' else None,
        instance=transaction,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard')

    return render(
        request,
        'finance/edit_transaction.html',
        {'form': form, 'transaction': transaction},
    )


@login_required
def delete_transaction(request, transaction_id):
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        user=request.user
    )

    if request.method == 'POST':
        transaction.delete()
        return redirect('dashboard')

    return render(
        request,
        'finance/delete_transaction.html',
        {'transaction': transaction}
    )

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(
        request,
        'registration/signup.html',
        {'form': form}
    )
