from django.contrib import admin
from .models import DepositRequest, WithdrawRequest


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'amount', 'status', 'requested_at')
    list_filter = ('status',)
    ordering = ('-requested_at',)
    search_fields = ('reference', 'user__username')


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'requested_at',
                    'bank_name', 'account_number', 'account_name')
    list_filter = ('status',)
    ordering = ('-requested_at',)
    search_fields = ('user__username', 'account_name', 'account_number')
