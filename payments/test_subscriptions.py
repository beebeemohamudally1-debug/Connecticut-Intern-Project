from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Invoice
from .subscriptions import (HandymanSubscription, SubscriptionReminder, add_months, has_active_subscription,
                            plan_options, plan_price, run_daily, subscribed_handymen)
from .test_invoicing import PASSWORD, make_user


def make_handyman(username, email=''):
    user = make_user(username, 'handyman')
    if email:
        user.email = email
        user.save()
    return user


class SubscriptionRulesTests(TestCase):
    def setUp(self):
        self.admin = make_user('adm', 'admin')
        self.handyman = make_handyman('kevin', 'kevin@example.com')
        self.sub = HandymanSubscription.for_handyman(self.handyman)
        self.today = timezone.localdate()

    def pay(self, invoice, amount=None):
        return invoice.record_payment(self.admin, amount=amount or invoice.total_amount, date_received=self.today,
                                      method='bank_transfer', reference='TRF-1', received=True, clear=True)

    def subscribe_and_pay(self, plan='monthly'):
        invoice = self.sub.subscribe(plan, by=self.handyman)
        self.pay(invoice)
        self.sub.refresh_from_db()
        return invoice

    # ---- prices
    def test_prices_and_yearly_discount(self):
        self.assertEqual(plan_price('monthly'), Decimal('1500.00'))
        self.assertEqual(plan_price('yearly'), Decimal('15300.00'))
        yearly = [p for p in plan_options() if p['code'] == 'yearly'][0]
        self.assertEqual(yearly['saving'], Decimal('2700.00'))
        with self.assertRaises(ValidationError):
            plan_price('weekly')

    def test_add_months_handles_short_months_and_year_end(self):
        from datetime import date
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 12, 15), 1), date(2027, 1, 15))
        self.assertEqual(add_months(date(2026, 3, 10), 12), date(2027, 3, 10))

    # ---- subscribing and paying
    def test_subscribing_issues_a_sub_invoice_and_nothing_is_listed_until_paid(self):
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        self.assertRegex(invoice.number, r'^SUB-\d{4}-0001$')
        self.assertEqual(invoice.total_amount, Decimal('1500.00'))
        self.assertEqual(self.sub.state, 'awaiting')
        self.assertFalse(has_active_subscription(self.handyman))

    def test_paying_activates_one_month_and_issues_a_receipt(self):
        invoice = self.subscribe_and_pay('monthly')
        self.assertEqual(self.sub.expires_on, add_months(self.today, 1) - timedelta(days=1))
        self.assertTrue(has_active_subscription(self.handyman))
        invoice.refresh_from_db()
        self.assertRegex(invoice.receipt.number, r'^RCT-\d{4}-\d{4}$')
        self.assertEqual(invoice.period_end, self.sub.expires_on)

    def test_yearly_plan_covers_twelve_months(self):
        self.subscribe_and_pay('yearly')
        self.assertEqual(self.sub.expires_on, add_months(self.today, 12) - timedelta(days=1))

    def test_renewal_continues_from_the_old_end_date_with_no_gap(self):
        self.subscribe_and_pay('monthly')
        self.sub.expires_on = self.today + timedelta(days=3)
        self.sub.save()
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        self.assertEqual(invoice.due_date, self.sub.expires_on)          # renewal is due on the last paid day
        old_end = self.sub.expires_on
        self.pay(invoice)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.expires_on, add_months(old_end + timedelta(days=1), 1) - timedelta(days=1))

    def test_a_lapsed_handyman_restarts_from_today(self):
        self.sub.expires_on = self.today - timedelta(days=5)
        self.sub.save()
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        self.pay(invoice)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.expires_on, add_months(self.today, 1) - timedelta(days=1))

    def test_no_grace_period(self):
        self.sub.expires_on = self.today - timedelta(days=1)
        self.sub.save()
        self.assertFalse(has_active_subscription(self.handyman))
        self.assertNotIn(self.handyman, subscribed_handymen())
        self.sub.expires_on = self.today                       # the last paid day still counts
        self.sub.save()
        self.assertTrue(has_active_subscription(self.handyman))
        self.assertIn(self.handyman, subscribed_handymen())

    def test_already_covered_handyman_only_changes_the_plan(self):
        self.subscribe_and_pay('monthly')
        self.assertIsNone(self.sub.subscribe('yearly', by=self.handyman))   # 30 days left, no invoice yet
        self.assertEqual(self.sub.plan, 'yearly')

    def test_only_full_amount_clears(self):
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        with self.assertRaises(ValidationError):
            self.pay(invoice, amount=Decimal('500.00'))
        self.assertFalse(has_active_subscription(self.handyman))

    # ---- plan change, cancel
    def test_changing_plan_replaces_the_open_invoice(self):
        first = self.sub.subscribe('monthly', by=self.handyman)
        second = self.sub.subscribe('yearly', by=self.handyman)
        first.refresh_from_db()
        self.assertEqual(first.status, Invoice.CANCELLED)
        self.assertEqual(second.total_amount, Decimal('15300.00'))
        self.assertEqual(self.sub.invoices.filter(status='issued').count(), 1)

    def test_cannot_change_plan_while_a_payment_is_being_processed(self):
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        invoice.record_payment(self.admin, amount=Decimal('500.00'), date_received=self.today,
                               method='cash', reference='', received=True, clear=False)
        with self.assertRaises(ValidationError):
            self.sub.subscribe('yearly', by=self.handyman)

    def test_cancel_keeps_access_until_the_end_and_stops_invoices(self):
        self.subscribe_and_pay('monthly')
        self.sub.cancel(by=self.handyman)
        self.assertEqual(self.sub.state, 'cancelling')
        self.assertTrue(has_active_subscription(self.handyman))
        run_daily(today=self.sub.expires_on - timedelta(days=2))
        self.assertEqual(self.sub.invoices.filter(status='issued').count(), 0)
        with self.assertRaises(ValidationError):
            self.sub.issue_invoice(by=self.admin)
        with self.assertRaises(ValidationError):
            self.sub.cancel(by=self.handyman)

    def test_cancelling_cancels_the_unpaid_invoice(self):
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        self.sub.cancel(by=self.handyman)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.CANCELLED)
        self.assertEqual(self.sub.state, 'cancelled')

    def test_can_subscribe_again_after_cancelling(self):
        self.sub.cancel(by=self.handyman)
        invoice = self.sub.subscribe('monthly', by=self.handyman)
        self.assertTrue(self.sub.auto_renew)
        self.assertIsNotNone(invoice)

    # ---- who may do what
    def test_other_handymen_cannot_manage_it(self):
        other = make_handyman('marc')
        with self.assertRaises(ValidationError):
            self.sub.subscribe('monthly', by=other)
        with self.assertRaises(ValidationError):
            self.sub.cancel(by=other)

    def test_only_handymen_can_have_a_subscription(self):
        with self.assertRaises(ValidationError):
            HandymanSubscription.for_handyman(make_user('cust', 'customer'))

    def test_admin_can_extend_and_it_is_recorded(self):
        self.sub.admin_extend(self.admin, 30)
        self.assertEqual(self.sub.expires_on, self.today + timedelta(days=29))
        self.assertIn('extended by 30 days', self.sub.admin_note)
        with self.assertRaises(ValidationError):
            self.sub.admin_extend(self.handyman, 30)
        with self.assertRaises(ValidationError):
            self.sub.admin_extend(self.admin, 0)


class DailyJobTests(TestCase):
    def setUp(self):
        self.admin = make_user('adm', 'admin')
        self.today = timezone.localdate()

    def test_issues_a_first_invoice_to_every_handyman_and_is_safe_to_rerun(self):
        make_handyman('a'), make_handyman('b')
        first = run_daily()
        self.assertEqual(first['invoices_issued'], 2)
        self.assertEqual(Invoice.objects.filter(invoice_type='subscription').count(), 2)
        self.assertEqual(run_daily()['invoices_issued'], 0)
        self.assertEqual(Invoice.objects.filter(invoice_type='subscription').count(), 2)

    def paid_sub(self, days_left):
        handyman = make_handyman('kevin', 'kevin@example.com')
        sub = HandymanSubscription.for_handyman(handyman)
        sub.expires_on = self.today + timedelta(days=days_left)
        sub.save()
        return sub

    def test_renewal_invoice_is_issued_seven_days_before_expiry(self):
        sub = self.paid_sub(7)
        run_daily()
        invoice = sub.invoices.get(status='issued')
        self.assertEqual(invoice.due_date, sub.expires_on)

    def test_no_invoice_earlier_than_that(self):
        sub = self.paid_sub(8)
        run_daily()
        self.assertEqual(sub.invoices.count(), 0)

    def test_reminders_go_out_once(self):
        sub = self.paid_sub(3)
        run_daily()
        run_daily()
        self.assertEqual(SubscriptionReminder.objects.filter(subscription=sub, kind__startswith='expiring:3:').count(), 1)

    def test_lapsed_handyman_gets_an_invoice_and_a_lapsed_message(self):
        sub = self.paid_sub(-1)
        run_daily()
        self.assertEqual(sub.invoices.filter(status='issued').count(), 1)
        self.assertTrue(SubscriptionReminder.objects.filter(subscription=sub, kind__startswith='lapsed:').exists())

    def test_cancelled_handymen_get_nothing(self):
        sub = self.paid_sub(2)
        sub.cancel(by=sub.handyman)
        run_daily()
        self.assertEqual(sub.invoices.count(), 0)
        self.assertEqual(sub.reminders.count(), 0)

    def test_customers_and_admins_are_ignored(self):
        make_user('cust', 'customer')
        self.assertEqual(run_daily()['subscriptions_created'], 0)


class SubscriptionPagesTests(TestCase):
    def setUp(self):
        self.admin = make_user('adm', 'admin')
        self.handyman = make_handyman('kevin', 'kevin@example.com')
        self.today = timezone.localdate()

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)

    def test_handyman_page_loads_for_a_new_handyman(self):
        self.login('kevin')
        response = self.client.get(reverse('payments:my_subscription'))
        self.assertContains(response, 'class="sidebar"')
        self.assertContains(response, 'Choose a plan')
        self.assertContains(response, '15,300.00')

    def test_subscribe_through_the_page_then_pay_then_receipt(self):
        self.login('kevin')
        self.client.post(reverse('payments:subscription_subscribe'), {'plan': 'monthly'})
        invoice = Invoice.objects.get(invoice_type='subscription')
        self.assertContains(self.client.get(reverse('payments:my_subscription')), invoice.number)

        self.client.logout()
        self.login('adm')
        self.assertEqual(self.client.get(reverse('payments:invoice_record_payment', args=[invoice.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('payments:invoice_list')).status_code, 200)
        self.client.post(reverse('payments:invoice_record_payment', args=[invoice.pk]), {
            'amount': '1500.00', 'date_received': self.today.isoformat(), 'method': 'bank_transfer',
            'reference': 'TRF-9', 'received': 'yes', 'action': 'clear'})
        self.assertTrue(has_active_subscription(self.handyman))

        self.client.logout()
        self.login('kevin')
        invoice.refresh_from_db()
        self.assertEqual(self.client.get(reverse('payments:subscription_receipt', args=[invoice.receipt.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse('payments:my_subscription')), 'Active')

    def test_another_handyman_cannot_open_the_receipt(self):
        sub = HandymanSubscription.for_handyman(self.handyman)
        invoice = sub.subscribe('monthly', by=self.handyman)
        invoice.record_payment(self.admin, amount=invoice.total_amount, date_received=self.today, method='cash',
                               reference='', received=True, clear=True)
        make_handyman('marc')
        self.login('marc')
        self.assertEqual(self.client.get(reverse('payments:subscription_receipt', args=[invoice.receipt.pk])).status_code, 404)

    def test_cancel_through_the_page(self):
        self.login('kevin')
        self.client.post(reverse('payments:subscription_subscribe'), {'plan': 'monthly'})
        self.client.post(reverse('payments:subscription_cancel'))
        self.assertFalse(HandymanSubscription.objects.get(handyman=self.handyman).auto_renew)

    def test_admin_list_issue_and_extend(self):
        self.login('adm')
        self.assertContains(self.client.get(reverse('payments:subscription_list')), 'kevin')
        self.client.post(reverse('payments:subscription_issue_invoice', args=[self.handyman.pk]))
        self.assertEqual(Invoice.objects.filter(invoice_type='subscription').count(), 1)
        self.client.post(reverse('payments:subscription_extend', args=[self.handyman.pk]), {'days': '10'})
        self.assertTrue(has_active_subscription(self.handyman))

    def test_only_admins_see_the_admin_page(self):
        self.login('kevin')
        self.assertEqual(self.client.get(reverse('payments:subscription_list')).status_code, 403)
        self.client.logout()
        self.login('adm')
        self.assertEqual(self.client.get(reverse('payments:my_subscription')).status_code, 403)

    def test_banner_shows_on_handyman_pages_until_subscribed(self):
        self.login('kevin')
        self.assertContains(self.client.get(reverse('payments:my_materials')), 'You are not subscribed yet.')
        HandymanSubscription.for_handyman(self.handyman).admin_extend(self.admin, 60)
        self.assertNotContains(self.client.get(reverse('payments:my_materials')), 'You are not subscribed yet.')


@override_settings(MIDDLEWARE=settings.MIDDLEWARE + ['payments.middleware.SubscriptionOnboardingMiddleware'])
class OnboardingTests(TestCase):
    """A new handyman is shown the plan page first, once per login session."""

    def setUp(self):
        self.admin = make_user('adm', 'admin')
        self.handyman = make_handyman('kevin')
        self.client.login(username='kevin', password=PASSWORD)
        self.dashboard = reverse('dashboard:handyman_dashboard')

    def test_new_handyman_is_sent_to_the_plan_page_once(self):
        response = self.client.get(self.dashboard)
        self.assertRedirects(response, reverse('payments:my_subscription'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(self.dashboard).status_code, 200)       # only the first time

    def test_a_handyman_who_has_paid_before_is_not_redirected(self):
        HandymanSubscription.for_handyman(self.handyman).admin_extend(self.admin, 30)
        self.assertEqual(self.client.get(self.dashboard).status_code, 200)

    def test_only_the_dashboard_home_is_redirected(self):
        self.assertEqual(self.client.get(reverse('payments:my_materials')).status_code, 200)

    def test_customers_are_never_redirected(self):
        make_user('cust', 'customer')
        self.client.logout()
        self.client.login(username='cust', password=PASSWORD)
        self.assertNotEqual(self.client.get(self.dashboard).status_code, 302)
