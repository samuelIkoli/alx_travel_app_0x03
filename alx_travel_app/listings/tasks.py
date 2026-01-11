from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_email(self, booking_data, user_email):
    """
    Send booking confirmation email asynchronously.
    """
    try:
        subject = f"Booking Confirmation - {booking_data.get('booking_id', 'New Booking')}"
        
        # Prepare context for email template
        context = {
            'booking': booking_data,
            'user_email': user_email,
            'booking_date': booking_data.get('created_at', timezone.now()),
            'confirmation_number': booking_data.get('confirmation_number', 'N/A'),
        }
        
        # Render HTML content
        html_content = render_to_string('listings/emails/booking_confirmation.html', context)
        text_content = strip_tags(html_content)  # Strip tags for plain text version
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
            cc=[settings.DEFAULT_FROM_EMAIL],  # CC to admin
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        email.attach_alternative(html_content, "text/html")
        
        # Optional: Add attachments if needed
        # attachment_path = '/path/to/file.pdf'
        # with open(attachment_path, 'rb') as file:
        #     email.attach('Booking_Details.pdf', file.read(), 'application/pdf')
        
        email.send(fail_silently=False)
        
        logger.info(f"Booking confirmation email sent successfully to {user_email}")
        return f"Email sent to {user_email}"
        
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email: {str(e)}")
        # Retry the task after 5 minutes
        self.retry(exc=e, countdown=300)  # 5 minutes delay


@shared_task
def send_booking_cancellation_email(booking_data, user_email):
    """
    Send booking cancellation email.
    """
    try:
        subject = f"Booking Cancelled - {booking_data.get('booking_id', 'Booking')}"
        
        context = {
            'booking': booking_data,
            'user_email': user_email,
            'cancellation_date': timezone.now(),
        }
        
        html_content = render_to_string('listings/emails/booking_cancellation.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Booking cancellation email sent to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")
        return False


@shared_task
def send_booking_reminder_email():
    """
    Send reminder emails for upcoming bookings (24 hours before).
    """
    try:
        from listings.models import Booking
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        tomorrow = timezone.now() + timedelta(days=1)
        
        # Get bookings starting tomorrow
        upcoming_bookings = Booking.objects.filter(
            start_date=tomorrow.date(),
            status='confirmed'
        )
        
        email_count = 0
        for booking in upcoming_bookings:
            try:
                user = booking.user
                subject = f"Reminder: Your booking tomorrow - {booking.listing.title}"
                
                context = {
                    'booking': booking,
                    'user': user,
                    'listing': booking.listing,
                }
                
                html_content = render_to_string('listings/emails/booking_reminder.html', context)
                text_content = strip_tags(html_content)
                
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=True,
                )
                
                email_count += 1
                logger.info(f"Sent reminder email to {user.email} for booking {booking.id}")
                
            except Exception as e:
                logger.error(f"Failed to send reminder for booking {booking.id}: {e}")
                continue
        
        return f"Sent {email_count} reminder emails"
        
    except Exception as e:
        logger.error(f"Error in send_booking_reminder_email: {e}")
        return f"Error: {str(e)}"


@shared_task
def send_daily_booking_summary():
    """
    Send daily booking summary to admin.
    """
    try:
        from listings.models import Booking
        from django.db.models import Count, Sum
        from datetime import date
        
        today = date.today()
        
        # Get today's statistics
        todays_bookings = Booking.objects.filter(created_at__date=today)
        confirmed_count = todays_bookings.filter(status='confirmed').count()
        cancelled_count = todays_bookings.filter(status='cancelled').count()
        total_revenue = todays_bookings.filter(status='confirmed').aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        context = {
            'date': today,
            'total_bookings': todays_bookings.count(),
            'confirmed_count': confirmed_count,
            'cancelled_count': cancelled_count,
            'total_revenue': total_revenue,
            'bookings': todays_bookings[:10],  # Last 10 bookings
        }
        
        subject = f"Daily Booking Summary - {today}"
        html_content = render_to_string('listings/emails/daily_summary.html', context)
        text_content = strip_tags(html_content)
        
        # Send to admin email(s)
        admin_emails = [settings.ADMIN_EMAIL] if hasattr(settings, 'ADMIN_EMAIL') else ['admin@example.com']
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Daily booking summary sent for {today}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")
        return False


@shared_task
def cleanup_old_bookings():
    """
    Clean up old cancelled bookings (older than 30 days).
    """
    try:
        from listings.models import Booking
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=30)
        old_cancelled = Booking.objects.filter(
            status='cancelled',
            updated_at__lt=cutoff_date
        )
        
        count = old_cancelled.count()
        old_cancelled.delete()
        
        logger.info(f"Cleaned up {count} old cancelled bookings")
        return f"Cleaned up {count} old cancelled bookings"
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_bookings: {e}")
        return f"Error: {str(e)}"