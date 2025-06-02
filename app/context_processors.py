from .models import DepositRequest


def deposit_notification(request):
    """
    Adds the number of PENDING DepositRequests to the admin context
    so the index template can pull it in.
    """
    pending_count = DepositRequest.objects.filter(status='PENDING').count()
    return {'deposit_pending_count': pending_count}
