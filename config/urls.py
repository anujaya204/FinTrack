from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from finance.views import (
    dashboard,
    all_transactions,
    add_transaction,
    edit_transaction,
    delete_transaction,
    signup
)


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', dashboard, name='dashboard'),

    path(
        'transactions/',
        all_transactions,
        name='all_transactions'
    ),

    path('add/', add_transaction, name='add_transaction'),

    path(
        'edit/<int:transaction_id>/',
        edit_transaction,
        name='edit_transaction'
    ),

    path(
        'delete/<int:transaction_id>/',
        delete_transaction,
        name='delete_transaction'
    ),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
    path(
    'signup/',
    signup,
    name='signup'
    ),
]