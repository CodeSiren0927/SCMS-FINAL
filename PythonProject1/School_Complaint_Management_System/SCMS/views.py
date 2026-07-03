from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json

# DATABASE RECTIFICATION: Form & Model Integrations
from .forms import StudentRegistrationForm
from .models import Complaint, StudentProfile, Notification, PurgedAccountLog  # IMPORTED PurgedAccountLog


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ==================== Authentication Views ====================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password'))
            if user:
                login(request, user)
                return redirect('admin_dashboard') if is_admin_or_staff(user) else redirect('profile')
    else:
        form = AuthenticationForm()
    return render(request, 'SCMS/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'SCMS/register.html', {'form': form})


@require_POST
def request_password_reset_view(request):
    """ Receives a user's email address to flag for admin password reset authorization. """
    email = request.POST.get('email')
    matching_users = User.objects.filter(email=email)

    if matching_users.exists():
        for user in matching_users:
            Notification.objects.create(
                user=user,
                message=f"PASSWORD_RESET_REQUEST:{email}",
                is_read=False
            )
        messages.success(request, "Security override request successfully transmitted to administration.")
    else:
        messages.info(request, "If that email is registered, a request patch has been piped to administration.")

    return redirect('login')


# ==================== Student Views ====================

@login_required
def submit_complaint_view(request):
    # Fallback to true if column is not migrated yet so the view doesn't throw AttributeErrors
    can_submit = getattr(request.user, 'can_submit_complaints', True)
    if not can_submit:
        messages.error(
            request,
            "SUBMISSION RESTRICTED: Your messaging privileges have been locked by an administrator. "
            "You can still access your profile account, but cannot transmit new complaints."
        )
        return redirect('profile')

    date_field = 'updated_at' if hasattr(Complaint, 'updated_at') else 'created_at'
    rejected_complaints = Complaint.objects.filter(student=request.user, status='Rejected').order_by(f'-{date_field}')

    if rejected_complaints.count() >= 5:
        latest_rejection = rejected_complaints.first()
        latest_rejection_time = getattr(latest_rejection, date_field)
        cooldown_expiry = latest_rejection_time + timedelta(hours=72)

        if timezone.now() < cooldown_expiry:
            time_remaining = cooldown_expiry - timezone.now()
            hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)

            messages.error(
                request,
                f"SYSTEM LOCKOUT: You have exceeded the limit of 5 rejected messages. "
                f"Transmission channel blocked for another {hours}h {minutes}m."
            )
            return redirect('profile')

    if request.method == 'POST':
        Complaint.objects.create(
            student=request.user,
            title=request.POST.get('title'),
            category=request.POST.get('category'),
            description=request.POST.get('description')
        )
        messages.success(request, "Your complaint has been submitted successfully.")
        return redirect('profile')
    return render(request, 'SCMS/submit_complaint.html')


@login_required
def profile_view(request):
    complaints = Complaint.objects.filter(student=request.user).order_by('-created_at')
    rejected_count = complaints.filter(status='Rejected').count()

    # Dynamic fallback helper if reverse target lookup isn't registered natively
    if hasattr(request.user, 'notifications'):
        notifications = request.user.notifications.all().order_by('-created_at')
    else:
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    unread_notifications = notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)

    return render(request, 'SCMS/profile.html', {
        'complaints': complaints,
        'notifications': notifications,
        'rejected_count': rejected_count
    })


@login_required
@require_POST
def delete_account_view(request):
    """
    Logs account termination data. The actual logging is now handled automatically
    by the pre_delete signal attached to the User model.
    """
    user = request.user
    logout(request)
    user.delete()  # Trigger pre_delete signal implicitly

    messages.success(request, "Your system identity has been purged successfully.")
    return redirect('login')


@login_required
def edit_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.user)

    if complaint.status != 'Pending':
        messages.error(request, "Access Denied: You cannot modify a log that has already been processed.")
        return redirect('profile')

    if request.method == 'POST':
        complaint.title = request.POST.get('title')
        complaint.category = request.POST.get('category')
        complaint.description = request.POST.get('description')
        complaint.save()
        messages.success(request, f"Log '{complaint.title}' has been modified.")

    return redirect('profile')


@login_required
def delete_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.user)

    if complaint.status not in ['Pending', 'Approved']:
        messages.error(request,
                       "Access Denied: Rejected transmission logs can only be cleared by System Administrators.")
        return redirect('profile')

    if request.method == 'POST':
        silent_delete = request.POST.get('silent_delete') == 'true'
        complaint._silent_delete = silent_delete
        complaint.delete()
        messages.success(request, "Transmission log permanently deleted.")

    return redirect('profile')


@login_required
@require_POST
def delete_notification_view(request, pk):
    """ Permanently removes an incoming transmission notification for the user. """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    silent_delete = request.POST.get('silent_delete') == 'true'
    notification._silent_delete = silent_delete
    notification.delete()
    messages.success(request, "Incoming transmission record cleared.")
    return redirect('profile')


# ==================== Admin Views ====================

@user_passes_test(is_admin_or_staff)
def admin_dashboard_view(request):
    """ Renders administration tracking along with the new system operations components. """
    complaints = Complaint.objects.exclude(status='Rejected').order_by('-created_at')
    pending_transmissions = Complaint.objects.filter(status='Pending').order_by('-created_at')
    all_users = User.objects.all().order_by('username')

    reset_notifs = Notification.objects.filter(message__startswith="PASSWORD_RESET_REQUEST:")
    reset_requests = []
    for notif in reset_notifs:
        email = notif.message.split("PASSWORD_RESET_REQUEST:")[-1]
        reset_requests.append({
            'id': notif.id,
            'email': email,
            'created_at': notif.created_at
        })

    # UPDATED: Fetch directly from the PurgedAccountLog model
    deleted_accounts = PurgedAccountLog.objects.all()[:50]  # Grabs the 50 most recent purged accounts

    return render(request, 'SCMS/admin_dashboard.html', {
        'complaints': complaints,
        'pending_transmissions': pending_transmissions,
        'pending_count': pending_transmissions.count(),
        'all_users': all_users,
        'reset_requests': reset_requests,
        'reset_count': len(reset_requests),
        'deleted_accounts': deleted_accounts
    })


@user_passes_test(is_admin_or_staff)
@require_POST
def confirm_password_reset_view(request, pk):
    """ Admin confirms that the user forgot password; resets password to a default string. """
    notification = get_object_or_404(Notification, pk=pk)
    user = notification.user

    user.set_password("ResetTempPass2026!")
    user.save()
    notification.delete()

    messages.success(request,
                     f"Security key override verified. Account '{user.username}' reset credentials configured to default string.")
    return redirect('admin_dashboard')


@user_passes_test(is_admin_or_staff)
def complaint_detail_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if not complaint.viewed:
        complaint.viewed = True
        complaint.status = 'Pending'
        complaint.save()
    return render(request, 'SCMS/complaint_detail.html', {'complaint': complaint})


@user_passes_test(is_admin_or_staff)
def update_complaint_status_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_remarks = request.POST.get('admin_remarks', '').strip()
        if new_status:
            complaint.status = new_status
            complaint.admin_remarks = admin_remarks
            complaint.save()
            messages.success(request, f"Complaint '{complaint.title}' marked as {new_status}.")
    return redirect('admin_dashboard')


@user_passes_test(is_admin_or_staff)
def restrict_user_complaints_view(request, user_id):
    """ Feature 2: Asynchronously restricts a user from submitting complaints without breaking account authentication. """
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)

        # Dynamically inject attribute or update field profile structure
        target_user.can_submit_complaints = False
        target_user.save()

        return JsonResponse({'status': 'success', 'message': f'User {target_user.username} restricted.'})
    return JsonResponse({'status': 'failed', 'message': 'Invalid access protocol.'}, status=400)


# ==================== Rejected Messages Management ====================

@user_passes_test(is_admin_or_staff)
def view_rejected_view(request):
    rejected = Complaint.objects.filter(status='Rejected').order_by('-created_at')
    return render(request, 'SCMS/rejected_list.html', {'rejected': rejected})


@user_passes_test(is_admin_or_staff)
def delete_complaint_view_admin(request, pk):
    """ Feature 1: Allows an administrator to clear logs directly while bypass-flagging signal notifications. """
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk)
        complaint._silent_delete = True
        complaint.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Notification cleared cleanly from tracking grid.'})

        messages.success(request, "Transmission permanently deleted without triggering alerts.")

    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))