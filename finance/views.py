from django.shortcuts import render,redirect, get_object_or_404
from .models import Transaction
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login


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

    transaction_query = Q(user=request.user)
    if transaction_filter != 'all':
        transaction_query &= Q(transaction_type=transaction_filter)
    if search_query:
        transaction_query &= (
            Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(transaction_type__icontains=search_query)
        )

    transactions = Transaction.objects.filter(transaction_query).order_by(
        '-date',
        '-created_at'
    )[:5]

    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'transactions': transactions,
        'transaction_filter': transaction_filter,
        'search_query': search_query,
    }

    return render(request, 'finance/dashboard.html', context)

@login_required
def add_transaction(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')

        Transaction.objects.create(
         user=request.user,
         amount=amount,
         transaction_type=transaction_type,
         category=category,
         date=date,
         description=description,
        )

        return redirect('dashboard')

    return render(request, 'finance/add_transaction.html')

@login_required
def edit_transaction(request, transaction_id):
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        user=request.user
    )

    if request.method == 'POST':
        transaction.amount = request.POST.get('amount')
        transaction.transaction_type = request.POST.get('transaction_type')
        transaction.category = request.POST.get('category')
        transaction.date = request.POST.get('date')
        transaction.description = request.POST.get('description')

        transaction.save()

        return redirect('dashboard')

    return render(
        request,
        'finance/edit_transaction.html',
        {'transaction': transaction}
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