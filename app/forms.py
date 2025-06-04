# dailysave/forms.py

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import ContributionPlan, Profile, PaymentProof, DepositRequest, WithdrawRequest
from django.utils.crypto import get_random_string
from django.contrib.auth import authenticate


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full Name", max_length=150, required=True)
    phone = forms.CharField(label="Phone Number", max_length=20, required=True)
    email = forms.EmailField(label="Email (optional)", required=False)
    terms = forms.BooleanField(
        label="I agree to the Terms & Conditions",
        required=True,
        error_messages={
            'required': 'You must agree to the Terms & Conditions.'}
    )

    class Meta:
        model = User
        # We'll store phone as the username field
        fields = ['phone', 'full_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['phone']
        user.first_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
    

class PlanForm(forms.ModelForm):
    class Meta:
        model = ContributionPlan
        fields = ['daily_amount']
        widgets = {
            'daily_amount': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'daily_amount': 'Select Daily Amount',
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']  # adjust as needed
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'user_type']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }


class PaymentProofForm(forms.ModelForm):
    # Date field: let user pick which date they are paying for
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Payment Date"
    )

    class Meta:
        model = PaymentProof
        fields = ['date', 'proof_file']
        widgets = {
            'proof_file': forms.FileInput(attrs={'class': 'form-control-file'}),
        }


class DepositRequestForm(forms.ModelForm):
    class Meta:
        model = DepositRequest
        fields = []  # we’ll set reference and amount in the view

    def save(self, commit=True, user=None, amount=None):
        """
        Overrides save() to auto-generate a reference and use the given amount.
        """
        deposit = super().save(commit=False)
        deposit.user = user
        deposit.amount = amount
        # Generate a 10-char alphanumeric reference, e.g. “DEP-X5Y3Z9K1L”
        deposit.reference = f"DEP-{get_random_string(8).upper()}"
        if commit:
            deposit.save()
        return deposit


class WithdrawRequestForm(forms.ModelForm):
    # Extra fields
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = WithdrawRequest
        fields = ['bank_name', 'account_number',
                  'account_name']  # Don't include amount

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        if not authenticate(username=self.user.username, password=password):
            raise forms.ValidationError("Invalid password.")

        return cleaned_data

    def save(self, commit=True, user=None, amount=None):
        withdraw = super().save(commit=False)
        withdraw.user = user
        withdraw.amount = amount
        if commit:
            withdraw.save()
        return withdraw
