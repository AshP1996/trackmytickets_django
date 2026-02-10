"""
Test script to verify email configuration
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email_config():
    """Test if email configuration is working"""
    print("Testing email configuration...")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    try:
        # Send test email
        send_mail(
            'Test Email - TrackMyTickets',
            'This is a test email to verify SMTP configuration is working correctly.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],  # Send to self
            fail_silently=False,
        )
        print("✅ Test email sent successfully!")
        print(f"Check your inbox at: {settings.EMAIL_HOST_USER}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

if __name__ == '__main__':
    test_email_config()
