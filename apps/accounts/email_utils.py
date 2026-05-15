"""
Utility functions for sending emails
"""
from django.core.mail import send_mail
from django.conf import settings
import hashlib
import random
import string
from datetime import timedelta
from django.utils import timezone


def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))


def _hash_otp(otp):
    """Hash an OTP for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def send_otp_email(email, otp, user_type='user'):
    """
    Send OTP email for password reset
    
    Args:
        email: Recipient email address
        otp: The OTP code to send
        user_type: Type of user ('user' or 'platform_admin')
    """
    subject = 'Password Reset OTP - TrackMyTickets'
    
    message = f"""
Hello,

You have requested to reset your password for TrackMyTickets.

Your OTP code is: {otp}

This code will expire in 15 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
TrackMyTickets Team
"""
    
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        send_mail(
            subject,
            message,
            from_email,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def create_reset_otp(user):
    """
    Create and save OTP for password reset.
    The OTP is hashed (SHA-256) before storage for security.
    
    Args:
        user: User or PlatformAdmin instance
        
    Returns:
        str: The generated OTP (plaintext — for sending via email)
    """
    otp = generate_otp()
    user.reset_otp = _hash_otp(otp)
    user.reset_otp_expires_at = timezone.now() + timedelta(minutes=15)
    user.save(update_fields=['reset_otp', 'reset_otp_expires_at'])
    return otp


def verify_reset_otp(user, otp):
    """
    Verify if the provided OTP is valid (compares SHA-256 hashes).
    
    Args:
        user: User or PlatformAdmin instance
        otp: The OTP to verify (plaintext from user input)
        
    Returns:
        bool: True if OTP is valid, False otherwise
    """
    if not user.reset_otp or not user.reset_otp_expires_at:
        return False
    
    if user.reset_otp != _hash_otp(otp):
        return False
    
    if timezone.now() > user.reset_otp_expires_at:
        return False
    
    return True


def clear_reset_otp(user):
    """Clear the reset OTP after successful password reset"""
    user.reset_otp = None
    user.reset_otp_expires_at = None
    user.save(update_fields=['reset_otp', 'reset_otp_expires_at'])
