# app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required
from .forms import PlanForm
from .models import ContributionPlan, PaymentProof, DepositRequest, WithdrawRequest
from django.utils import timezone
from .forms import UserUpdateForm, ProfileUpdateForm
from app.models import Profile
from .forms import PaymentProofForm, DepositRequestForm, WithdrawRequestForm
from datetime import date as dt_date
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
import csv
import calendar
from django.db.models import Count
from django.core.mail import mail_admins


def index(request):
    return render(request, 'app/index.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            phone = form.cleaned_data.get('phone')
            raw_password = form.cleaned_data.get('password1')

            # Instead of logging in, show a success message and redirect to login
            messages.success(
                request, 'Registration successful! You can now log in.')
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'app/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        phone = request.POST.get('username')  # matches form’s name="username"
        password = request.POST.get('password')
        user = authenticate(username=phone, password=password)


        if user is not None:
            login(request, user)
            profile, created = Profile.objects.get_or_create(
                user=user)  # Moved here
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid phone or password')

    return render(request, 'app/login.html')



def logout_view(request):
    logout(request)
    return redirect('index')



def forgot_password_step1(request):
    return render(request, 'app/forgot_password_step1.html')


def forgot_password_step2(request):
    return render(request, 'app/forgot_password_step2.html')


def forgot_password_step3(request):
    return render(request, 'app/forgot_password_step3.html')


@login_required
def payment_history(request):
    """
    Show the user all past PaymentProofs, in descending order by date.
    """
    # Fetch all proofs for this user, newest first
    proofs = PaymentProof.objects.filter(
        user=request.user).order_by('-date', '-uploaded_at')

    # Build a list of dicts containing date, amount, status, proof_url
    history = []
    for proof in proofs:
        # The daily_amount comes from the associated plan
        amount = proof.plan.daily_amount
        history.append({
            'date': proof.date,
            'amount': amount,
            'status': proof.status,
            'proof_url': proof.proof_file.url,
            'id': proof.id,
        })

    return render(request, 'app/payment_history.html', {
        'history': history,
    })


@login_required
def profile(request):
    """
    Display and process the user’s profile-edit page.
    - Allows changing first_name, last_name, email via UserUpdateForm.
    - Allows uploading a new image and changing user_type via ProfileUpdateForm.
    """
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(
            request.POST,
            request.FILES,              # ← crucial to include request.FILES
            instance=request.user.profile
        )
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'app/profile.html', {
        'u_form': u_form,
        'p_form': p_form,
    })


def terms_view(request):
    return render(request, 'app/terms.html')


@login_required
def choose_plan(request):
    now = timezone.localtime()
    current_month = now.month
    current_year = now.year

    try:
        plan_obj = ContributionPlan.objects.get(
            user=request.user,
            month=current_month,
            year=current_year
        )
        is_existing = True
    except ContributionPlan.DoesNotExist:
        plan_obj = None
        is_existing = False

    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan_obj)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.month = current_month
            plan.year = current_year
            plan.save()
            if is_existing:
                messages.success(
                    request, f"Your daily plan has been updated to ₦{plan.daily_amount}.")
            else:
                messages.success(
                    request, f"Your daily plan of ₦{plan.daily_amount}/day has been saved for {current_month}/{current_year}.")
            return redirect('dashboard')
    else:
        form = PlanForm(instance=plan_obj) if plan_obj else PlanForm()

    return render(request, 'app/choose_plan.html', {
        'form': form,
        'is_existing': is_existing,
        'now': now,
    })


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated.')
            # Redirect to dashboard after saving:
            return redirect('dashboard')
        else:
            # If either form is invalid, Django will re-render the page with errors
            messages.error(request, 'Please fix the errors below.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
    }
    return render(request, 'app/profile.html', context)


@login_required
def upload_proof(request):
    # Determine current month/year and the user’s plan object
    now = timezone.localtime()
    current_month = now.month
    current_year = now.year

    try:
        plan = ContributionPlan.objects.get(
            user=request.user,
            month=current_month,
            year=current_year
        )
    except ContributionPlan.DoesNotExist:
        messages.error(
            request, "You must choose a contribution plan before uploading payment proof.")
        return redirect('choose_plan')

    if request.method == 'POST':
        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            proof_date = form.cleaned_data['date']
            # Prevent future dates or duplicate entries
            if proof_date > dt_date.today():
                form.add_error(
                    'date', "Cannot upload proof for a future date.")
            else:
                # Check for existing proof for that day
                existing = PaymentProof.objects.filter(
                    user=request.user,
                    plan=plan,
                    date=proof_date
                ).first()
                if existing:
                    form.add_error(
                        'date', "You already uploaded proof for that date.")
                else:
                    payment_proof = form.save(commit=False)
                    payment_proof.user = request.user
                    payment_proof.plan = plan
                    payment_proof.status = 'PENDING'
                    payment_proof.save()
                    messages.success(
                        request, f"Proof for {proof_date} uploaded successfully. Awaiting approval.")
                    return redirect('dashboard')
    else:
        form = PaymentProofForm()

    return render(request, 'app/upload_proof.html', {'form': form})


# ────────────────────────────────────────────────────────────────────────────
# Collector/Admin Interface
# ────────────────────────────────────────────────────────────────────────────

@staff_member_required
def collector_dashboard(request):
    """
    Show all pending proofs for this month so the collector can approve/reject.
    """
    from .models import PaymentProof

    # Only Pending proofs
    pending_proofs = PaymentProof.objects.filter(
        status='PENDING').order_by('uploaded_at')

    return render(request, 'app/collector_dashboard.html', {
        'pending_proofs': pending_proofs,
    })


@staff_member_required
def approve_proof(request, proof_id):
    """
    Mark a PaymentProof as APPROVED.
    """
    from .models import PaymentProof

    proof = PaymentProof.objects.get(pk=proof_id)
    proof.status = 'APPROVED'
    proof.save()
    messages.success(
        request, f"Payment for {proof.user.username} on {proof.date} approved.")
    return redirect('collector_dashboard')


@staff_member_required
def reject_proof(request, proof_id):
    """
    Mark a PaymentProof as REJECTED.
    """
    from .models import PaymentProof

    proof = PaymentProof.objects.get(pk=proof_id)
    proof.status = 'REJECTED'
    proof.save()
    messages.error(
        request, f"Payment for {proof.user.username} on {proof.date} rejected.")
    return redirect('collector_dashboard')


@staff_member_required
def monthly_report(request):
    """
    Generate and display (and allow CSV download of) a report for the CURRENT month.
    Columns: Username, Total Paid, Collector Fee, Refund Amount.
    """
    from .models import ContributionPlan, PaymentProof

    now = timezone.localtime()
    current_month = now.month
    current_year = now.year

    # Fetch all users who have a ContributionPlan this month
    plans = ContributionPlan.objects.filter(
        month=current_month, year=current_year).select_related('user')

    report_data = []
    for plan in plans:
        user = plan.user
        daily_amount = plan.daily_amount

        # Count APPROVED proofs for this user/plan
        approved_count = PaymentProof.objects.filter(
            user=user, plan=plan, status='APPROVED'
        ).count()

        total_paid = approved_count * daily_amount
        collector_fee = daily_amount
        refund = total_paid - collector_fee

        report_data.append({
            'username': user.username,
            'full_name': user.get_full_name(),
            'total_paid': total_paid,
            'collector_fee': collector_fee,
            'refund': refund,
        })

    # If “download=csv” query param, return a CSV response
    if request.GET.get('download') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="monthly_report_{current_month}_{current_year}.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ['Username', 'Full Name', 'Total Paid', 'Collector Fee', 'Refund'])
        for row in report_data:
            writer.writerow([
                row['username'],
                row['full_name'],
                f"₦{row['total_paid']}",
                f"₦{row['collector_fee']}",
                f"₦{row['refund']}"
            ])
        return response

    # Otherwise, render HTML table
    return render(request, 'app/monthly_report.html', {
        'report_data': report_data,
        'month': current_month,
        'year': current_year,
    })


@login_required
def payment_detail(request, proof_id):
    """
    Show details for a specific PaymentProof.
    """
    proof = get_object_or_404(PaymentProof, pk=proof_id, user=request.user)
    return render(request, 'app/payment_detail.html', {'proof': proof})


@login_required
def dashboard(request):
    now = timezone.localtime()
    current_month = now.month
    current_year = now.year

    registration_date = request.user.date_joined.date()

    try:
        plan = ContributionPlan.objects.get(
            user=request.user,
            month=current_month,
            year=current_year
        )
    except ContributionPlan.DoesNotExist:
        plan = None

    if plan:
        proofs = PaymentProof.objects.filter(user=request.user, plan=plan)
    else:
        proofs = PaymentProof.objects.none()

    # Calculate totals (as before)…
    if plan:
        approved_count = proofs.filter(status='APPROVED').count()
        total_paid = approved_count * plan.daily_amount
        collector_fee = plan.daily_amount
        refund_amount = total_paid - collector_fee
    else:
        total_paid = 0
        collector_fee = 0
        refund_amount = 0

    # Build calendar_days (as before)…
    _, num_days = calendar.monthrange(current_year, current_month)
    today = dt_date.today()

    calendar_days = []
    for day in range(1, num_days + 1):
        check_date = dt_date(current_year, current_month, day)
        if check_date < registration_date or check_date < today:
            status = 'MISSED'
        else:
            status = 'FUTURE'

        proof = proofs.filter(date=check_date).first()
        if proof:
            status = proof.status
            proof_id = proof.id
        else:
            proof_id = None

        calendar_days.append({
            'day': day,
            'status': status,
            'proof_id': proof_id
        })

    recent_payments = proofs.order_by('-uploaded_at')[:3] if plan else []

    context = {
        'plan': plan,
        'now': now,
        'calendar_days': calendar_days,
        'recent_payments': recent_payments,
        'total_paid': total_paid,
        'collector_fee': collector_fee,
        'refund_amount': refund_amount,
    }
    return render(request, 'app/dashboard.html', context)


@login_required
def deposit_request(request):
    """
    On GET: show a page “Deposit Request.”  
    On POST: generate reference, notify admin, and show a “Deposit Reference Generated” page.
    """
    now = timezone.localtime()
    try:
        plan = ContributionPlan.objects.get(
            user=request.user,
            month=now.month,
            year=now.year
        )
    except ContributionPlan.DoesNotExist:
        messages.error(request, "You must choose a contribution plan first.")
        return redirect('choose_plan')

    amount = plan.daily_amount

    if request.method == 'POST':
        form = DepositRequestForm(request.POST)
        if form.is_valid():
            deposit = form.save(user=request.user, amount=amount)
            # Notify admins via email that a new deposit reference was created:
            subject = f"New Deposit Reference: {deposit.reference}"
            message = (
                f"User: {request.user.username} ({request.user.email})\n"
                f"Deposit Reference: {deposit.reference}\n"
                f"Amount: ₦{deposit.amount}\n"
                f"Requested At: {deposit.requested_at}\n\n"
                "Please be on standby to expect payment and approve once proof is uploaded."
            )
            mail_admins(subject, message)

            # Instead of redirect, render a “Success” page:
            return render(request, 'app/deposit_success.html', {
                'reference': deposit.reference,
                'amount': amount,
            })
    else:
        form = DepositRequestForm()

    return render(request, 'app/deposit_request.html', {
        'form': form,
        'amount': amount,
    })


@login_required
def withdraw_request(request):
    """
    On GET:
      If no net_refund, show “No funds to withdraw yet” then auto-redirect after a few seconds.
      Otherwise, show the withdraw form.
    On POST: create a WithdrawRequest and show a “Withdraw Submitted” page.
    """
    now = timezone.localtime()
    try:
        plan = ContributionPlan.objects.get(
            user=request.user,
            month=now.month,
            year=now.year
        )
    except ContributionPlan.DoesNotExist:
        messages.error(request, "You must choose a contribution plan first.")
        return redirect('choose_plan')

    approved_count = PaymentProof.objects.filter(
        user=request.user,
        plan=plan,
        status='APPROVED'
    ).count()

    total_paid = approved_count * plan.daily_amount
    collector_fee = plan.daily_amount
    net_refund = total_paid - collector_fee

    if net_refund <= 0:
        # Show a temporary “No Funds” page that auto-redirects back after 3 seconds
        return render(request, 'app/withdraw_none.html')

    if request.method == 'POST':
        form = WithdrawRequestForm(request.POST)
        if form.is_valid():
            withdraw = form.save(user=request.user, amount=net_refund)
            return render(request, 'app/withdraw_success.html', {
                'amount': net_refund,
            })
    else:
        form = WithdrawRequestForm()

    return render(request, 'app/withdraw_request.html', {
        'form': form,
        'net_refund': net_refund,
    })


@login_required  # or allow anonymous if you want public access
def how_it_works(request):
    return render(request, 'app/how_it_works.html')


def privacy_policy_view(request):
    return render(request, 'app/privacy_policy.html')
