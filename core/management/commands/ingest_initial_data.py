# core/management/commands/ingest_initial_data.py
from django.core.management.base import BaseCommand
from core.tasks import import_customer_data_task, import_loan_data_task

class Command(BaseCommand):
    help = 'Ingests initial customer and loan data from Excel files using Celery tasks.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data ingestion tasks...'))

        # Enqueue the Celery tasks
        import_customer_data_task.delay()
        import_loan_data_task.delay()

        self.stdout.write(self.style.SUCCESS('Data ingestion tasks enqueued. Check Celery worker logs for progress.'))