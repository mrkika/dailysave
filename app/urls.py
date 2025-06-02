# app/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password_step1, name='forgot_password_step1'),
    path('forgot-password/step2/', views.forgot_password_step2, name='forgot_password_step2'),
    path('forgot-password/step3/', views.forgot_password_step3, name='forgot_password_step3'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('terms/', views.terms_view,    name='terms'),
    path('choose-plan/', views.choose_plan, name='choose_plan'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('upload-proof/', views.upload_proof, name='upload_proof'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('payment/<int:proof_id>/', views.payment_detail, name='payment_detail'),
    path('deposit-request/', views.deposit_request, name='deposit_request'),
    path('withdraw-request/', views.withdraw_request, name='withdraw_request'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),



    path('collector/dashboard/', views.collector_dashboard, name='collector_dashboard'),
    path('collector/proof/<int:proof_id>/approve/', views.approve_proof, name='approve_proof'),
    path('collector/proof/<int:proof_id>/reject/', views.reject_proof, name='reject_proof'),
    path('collector/report/', views.monthly_report, name='monthly_report'),
    # Later: deposit, withdraw, update-plan, upload-proof, etc.
    path(
        'password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            success_url='/accounts/password-change-done/'
        ),
        name='password_change'
    ),
    path(
        'password-change-done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html'
        ),
        name='password_change_done'
    ),
]
