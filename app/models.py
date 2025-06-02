from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save


class ContributionPlan(models.Model):
    DAILY_CHOICES = [
        (500, '₦500 / day'),
        (1000, '₦1,000 / day'),
        (5000, '₦5,000 / day'),
        (10000, '₦10,000 / day'),
        (20000, '₦20,000 / day'),
        (50000, '₦50,000 / day'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    daily_amount = models.PositiveIntegerField(choices=DAILY_CHOICES)
    month = models.IntegerField()  # 1–12
    year = models.IntegerField()  # e.g. 2025
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.username} – ₦{self.daily_amount}/day ({self.month}/{self.year})"


class PaymentProof(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(ContributionPlan, on_delete=models.CASCADE)
    date = models.DateField()
    proof_file = models.FileField(upload_to='payment_proofs/')
    STATUS_CHOICES = [
        ('PENDING',   'Pending'),
        ('APPROVED',  'Approved'),
        ('REJECTED',  'Rejected'),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PENDING')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'plan', 'date')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.user.username} – {self.date} – {self.status}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    user_type = models.CharField(
        max_length=20,
        choices=(('client', 'Client'), ('professional', 'Professional')),
        default='client'
    )
    # Add this line (if you want users to upload a photo)
    photo = models.ImageField(
        upload_to='profile_pics/',
        default='profile_pics/default.jpg',
        blank=True
    )

    def __str__(self):
        return f"{self.user.username} Profile"

# Optionally, if you don’t already have a signal to create Profile when User is created:


class DepositRequest(models.Model):
    """
    When a user clicks “Deposit,” they get a unique reference.
    The collector can later mark it as “Received” or “Ignored.”
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference = models.CharField(max_length=20, unique=True)
    amount = models.PositiveIntegerField()  # could be plan.daily_amount or custom
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('PENDING', 'Pending'), ('RECEIVED', 'Received'),
                 ('CANCELLED', 'Cancelled')],
        default='PENDING'
    )

    def __str__(self):
        return f"{self.user.username} – Ref {self.reference} – ₦{self.amount}"


class WithdrawRequest(models.Model):
    """
    At month-end (or any time), a user can request a withdrawal of their net refund.
    Collector will mark it “Processed” or “Denied.”
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=12,
        choices=[('PENDING', 'Pending'), ('PROCESSED',
                                          'Processed'), ('DENIED', 'Denied')],
        default='PENDING'
    )

    def __str__(self):
        return f"{self.user.username} – Withdraw ₦{self.amount} – {self.status}"
