from datetime import date, timedelta
import json
import re
from html import unescape
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import translation

from .forms import TransactionForm
from .models import Transaction


try:
    settings.SECRET_KEY
except ImproperlyConfigured:
    # Allow isolated tests without local secrets; never used by the application.
    settings.SECRET_KEY = 'test-only-secret-key'


class TransactionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='alice',
            password='strong-password-123',
        )
        cls.other_user = User.objects.create_user(
            username='bob',
            password='strong-password-123',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def create_transaction(self, user=None, **overrides):
        values = {
            'user': user or self.user,
            'amount': '25.00',
            'transaction_type': 'expense',
            'category': 'Food',
            'date': date(2026, 9, 20),
            'description': 'Lunch',
        }
        values.update(overrides)
        return Transaction.objects.create(**values)

class TransactionViewTests(TransactionTestCase):
    def test_transaction_pages_require_login(self):
        self.client.logout()
        protected_urls = (
            reverse('dashboard'),
            reverse('all_transactions'),
            reverse('add_transaction'),
        )

        transaction = self.create_transaction()
        protected_urls += (
            reverse('edit_transaction', args=[transaction.id]),
            reverse('delete_transaction', args=[transaction.id]),
        )

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                )

    def test_all_transactions_and_mutations_are_user_isolated(self):
        own_transaction = self.create_transaction(description='Alice transaction')
        other_transaction = self.create_transaction(
            user=self.other_user,
            category='Private',
            description='Bob transaction',
        )

        response = self.client.get(reverse('all_transactions'))

        self.assertContains(response, 'Alice transaction')
        self.assertNotContains(response, 'Bob transaction')
        self.assertEqual(
            self.client.get(
                reverse('edit_transaction', args=[other_transaction.id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse('delete_transaction', args=[other_transaction.id])
            ).status_code,
            404,
        )
        self.assertTrue(Transaction.objects.filter(id=own_transaction.id).exists())
        self.assertTrue(Transaction.objects.filter(id=other_transaction.id).exists())

    def test_add_validation_shows_errors_and_preserves_values(self):
        response = self.client.post(
            reverse('add_transaction'),
            {
                'amount': '-5',
                'transaction_type': 'transfer',
                'category': '   ',
                'date': '',
                'description': 'Keep this description',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amount must be greater than 0.')
        self.assertContains(response, 'Select a valid choice.')
        self.assertContains(response, 'Category cannot be blank.')
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Keep this description')
        self.assertFalse(Transaction.objects.exists())

    def test_add_edit_and_delete_transaction(self):
        add_response = self.client.post(
            reverse('add_transaction'),
            {
                'amount': '125.50',
                'transaction_type': 'income',
                'category': 'Salary',
                'date': '2026-09-21',
                'description': 'Monthly salary',
            },
        )

        self.assertRedirects(add_response, reverse('dashboard'))
        transaction = Transaction.objects.get(user=self.user)
        self.assertEqual(transaction.amount, 125.50)
        self.assertEqual(transaction.transaction_type, 'income')

        edit_response = self.client.post(
            reverse('edit_transaction', args=[transaction.id]),
            {
                'amount': '130.00',
                'transaction_type': 'expense',
                'category': 'Rent',
                'date': '2026-09-22',
                'description': 'Updated transaction',
            },
        )

        self.assertRedirects(edit_response, reverse('dashboard'))
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 130.00)
        self.assertEqual(transaction.category, 'Rent')

        delete_response = self.client.post(
            reverse('delete_transaction', args=[transaction.id])
        )

        self.assertRedirects(delete_response, reverse('dashboard'))
        self.assertFalse(Transaction.objects.filter(id=transaction.id).exists())

    def test_search_and_filter_work_together(self):
        self.create_transaction(category='Food', description='Dinner')
        self.create_transaction(
            transaction_type='income',
            category='Food',
            description='Food reimbursement',
        )
        self.create_transaction(category='Rent', description='Monthly rent')

        response = self.client.get(
            reverse('all_transactions'),
            {'type': 'expense', 'search': 'food'},
        )

        self.assertContains(response, 'Dinner')
        self.assertNotContains(response, 'Food reimbursement')
        self.assertNotContains(response, 'Monthly rent')

    def test_all_transactions_are_newest_first_and_paginated(self):
        for index in range(12):
            self.create_transaction(
                category=f'Category {index}',
                date=date(2026, 9, 1) + timedelta(days=index),
            )

        first_page = self.client.get(
            reverse('all_transactions'),
            {'type': 'expense', 'search': 'Category', 'page': 1},
        )
        second_page = self.client.get(
            reverse('all_transactions'),
            {'type': 'expense', 'search': 'Category', 'page': 2},
        )

        self.assertEqual(first_page.context['page_obj'].paginator.count, 12)
        self.assertEqual(len(first_page.context['page_obj'].object_list), 10)
        self.assertEqual(len(second_page.context['page_obj'].object_list), 2)
        self.assertContains(first_page, 'type=expense')
        self.assertContains(first_page, 'search=Category')
        self.assertContains(first_page, 'page=2')
        self.assertContains(first_page, 'Category 11')
        self.assertNotContains(first_page, 'Category 0')


class ReviewRegressionTests(TransactionTestCase):
    def payload(self, **overrides):
        data = {
            'amount': '12.50', 'transaction_type': 'expense',
            'category': 'Food', 'date': '2026-09-20',
            'description': 'Preserve this description',
        }
        data.update(overrides)
        return data

    def test_empty_posts_show_required_errors_without_changing_data(self):
        transaction = self.create_transaction()
        for url in (reverse('add_transaction'), reverse('edit_transaction', args=[transaction.pk])):
            with self.subTest(url=url):
                response = self.client.post(url, {})
                self.assertTrue(response.context['form'].is_bound)
                self.assertContains(response, 'This field is required.')
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 25)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_foreign_edit_post_and_delete_get_are_rejected(self):
        transaction = self.create_transaction(user=self.other_user)
        self.assertEqual(self.client.post(
            reverse('edit_transaction', args=[transaction.pk]), self.payload()
        ).status_code, 404)
        self.assertEqual(self.client.get(
            reverse('delete_transaction', args=[transaction.pk])
        ).status_code, 404)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 25)
        self.assertEqual(transaction.user, self.other_user)

    def test_posted_owner_is_ignored_on_add_and_edit(self):
        self.client.post(reverse('add_transaction'), self.payload(user=self.other_user.pk))
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.user, self.user)
        self.client.post(reverse('edit_transaction', args=[transaction.pk]),
                         self.payload(user=self.other_user.pk))
        transaction.refresh_from_db()
        self.assertEqual(transaction.user, self.user)

    def test_delete_get_does_not_delete_and_mutations_require_csrf(self):
        transaction = self.create_transaction()
        self.assertEqual(self.client.get(reverse('delete_transaction', args=[transaction.pk])).status_code, 200)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in (reverse('add_transaction'), reverse('edit_transaction', args=[transaction.pk]),
                    reverse('delete_transaction', args=[transaction.pk])):
            with self.subTest(url=url):
                self.assertEqual(client.post(url, self.payload()).status_code, 403)
        self.assertEqual(Transaction.objects.count(), 1)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 25)

    def test_invalid_edit_preserves_values_and_database(self):
        transaction = self.create_transaction()
        response = self.client.post(reverse('edit_transaction', args=[transaction.pk]),
                                    self.payload(amount='0', category='Changed'))
        self.assertContains(response, 'Amount must be greater than 0.')
        self.assertContains(response, 'value="0"')
        self.assertContains(response, 'value="Changed"')
        self.assertContains(response, 'value="2026-09-20"')
        self.assertContains(response, 'Preserve this description')
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 25)
        self.assertEqual(transaction.category, 'Food')

    def test_form_rejects_invalid_amounts_dates_categories_and_types(self):
        cases = {'amount': ['0', '-1', 'NaN', 'Infinity', '1.001', '100000000', 'abc'],
                 'date': ['', '2026-02-30', 'not-a-date'],
                 'category': ['   ', 'x' * 101], 'transaction_type': ['transfer', '']}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    form = TransactionForm(self.payload(**{field: value}))
                    self.assertFalse(form.is_valid())
                    self.assertIn(field, form.errors)

    def test_search_filter_pagination_links_round_trip(self):
        search = 'Food & tea + / café'
        transactions = [self.create_transaction(category=search) for _ in range(12)]
        # Even identical timestamps must have a stable pagination order.
        Transaction.objects.update(created_at=transactions[0].created_at)
        self.create_transaction(category=search, transaction_type='income')
        self.create_transaction(category=search, user=self.other_user)
        response = self.client.get(reverse('all_transactions'), {'search': search, 'type': 'expense'})
        self.assertEqual(response.context['page_obj'].paginator.count, 12)
        link = unescape(re.search(r'href="([^"]+)">Next</a>', response.content.decode()).group(1))
        self.assertEqual(parse_qs(urlsplit(link).query)['search'], [search])
        second = self.client.get(reverse('all_transactions') + link)
        self.assertEqual(second.context['page_obj'].number, 2)
        ids = [item.pk for item in response.context['page_obj']] + [item.pk for item in second.context['page_obj']]
        self.assertEqual(ids, [item.pk for item in reversed(transactions)])

    def test_invalid_pages_and_filters_are_handled(self):
        self.create_transaction()
        for page in ('bad', '0', '-1', '999'):
            response = self.client.get(reverse('all_transactions'), {'page': page, 'type': 'invalid'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['transaction_filter'], 'all')
        response = self.client.get(reverse('all_transactions'), {'search': 'no match'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_chart_json_and_edit_date_are_safe_under_localization(self):
        category = '</script><script>alert(1)</script>&'
        transaction = self.create_transaction(category=category, amount='1234.56')
        with translation.override('de'):
            response = self.client.get(reverse('dashboard'))
            edit = self.client.get(reverse('edit_transaction', args=[transaction.pk]))
        self.assertContains(edit, 'value="2026-09-20"')
        html = response.content.decode()
        def chart_data(element_id):
            raw = re.search(r'<script id="' + element_id + r'" type="application/json">(.*?)</script>', html).group(1)
            self.assertNotIn('<', raw)
            return json.loads(raw)
        self.assertEqual(chart_data('income-expense-data'), [0, 1234.56])
        self.assertEqual(chart_data('expense-category-data'), [{'category': category, 'total': 1234.56}])

    def test_login_errors_username_and_destination_are_preserved(self):
        self.client.logout()
        response = self.client.post(reverse('login'), {
            'username': 'alice', 'password': 'wrong', 'next': reverse('all_transactions'),
        })
        self.assertContains(response, 'Please enter a correct username and password.')
        self.assertContains(response, 'value="alice"')
        self.assertContains(response, 'name="next" value="/transactions/"')


class DashboardAnalyticsTests(TransactionTestCase):
    def test_dashboard_analytics_are_limited_to_current_user(self):
        self.create_transaction(
            amount='100.00',
            transaction_type='income',
            category='Salary',
        )
        self.create_transaction(
            amount='30.00',
            transaction_type='expense',
            category='Food',
        )
        self.create_transaction(
            user=self.other_user,
            amount='900.00',
            transaction_type='expense',
            category='Secret',
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['total_income'], 100)
        self.assertEqual(response.context['total_expenses'], 30)
        self.assertEqual(
            response.context['expense_categories'],
            [{'category': 'Food', 'total': 30.0}],
        )
