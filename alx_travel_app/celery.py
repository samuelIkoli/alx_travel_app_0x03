import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app_0x03.settings')

app = Celery('alx_travel_app_0x03')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'check-low-stock-every-12-hours': {
        'task': 'crm.tasks.check_and_notify_low_stock',
        'schedule': crontab(hour='*/12', minute=0),  # Every 12 hours
        'args': (10,),  # threshold of 10
    },
    'send-daily-booking-summary': {
        'task': 'listings.tasks.send_daily_booking_summary',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    'cleanup-old-bookings': {
        'task': 'listings.tasks.cleanup_old_bookings',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')