from django.core.management.base import BaseCommand

from payments.subscriptions import run_daily


class Command(BaseCommand):
    help = ("Issue handyman subscription invoices (new, renewal and after a lapse) and send expiry reminders. "
            "Run it once a day.")

    def handle(self, *args, **options):
        result = run_daily()
        self.stdout.write(self.style.SUCCESS(
            f"Subscriptions created: {result['subscriptions_created']}, invoices issued: {result['invoices_issued']}, "
            f"messages sent: {result['messages_sent']}"))
