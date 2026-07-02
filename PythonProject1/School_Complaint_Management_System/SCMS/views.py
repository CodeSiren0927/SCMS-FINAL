from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Complaint, StudentProfile, Notification
from .forms import StudentRegistrationForm


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
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'SCMS/register.html', {'form': form})


# ==================== Student Views ====================

@login_required
def submit_complaint_view(request):
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

    # Directly pull from the established related_name connection
    notifications = request.user.notifications.all().order_by('-created_at')

    unread_notifications = notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)

    return render(request, 'SCMS/profile.html', {
        'complaints': complaints,
        'notifications': notifications
    })


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

    if complaint.status != 'Pending':
        messages.error(request, "Access Denied: You cannot delete a log that has already been processed.")
        return redirect('profile')

    if request.method == 'POST':
        complaint.delete()
        messages.success(request, "Transmission log permanently deleted.")

    return redirect('profile')


@login_required
def delete_notification_view(request, pk):
    """ Permanently removes an incoming transmission notification for the user. """
    if request.method == 'POST':
        # Cleaned up to match the definitive 'user' ForeignKey field name
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        messages.success(request, "Incoming transmission record cleared.")
    return redirect('profile')


# ==================== Admin Views ====================

@user_passes_test(is_admin_or_staff)
def admin_dashboard_view(request):
    complaints = Complaint.objects.exclude(status='Rejected').order_by('-created_at')
    return render(request, 'SCMS/admin_dashboard.html', {'complaints': complaints})


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

            # Saving here triggers the database post_save signal automatically,
            # safely committing the precise Notification record with no extra code needed!
            complaint.save()

            messages.success(request, f"Complaint '{complaint.title}' marked as {new_status}.")
    return redirect('admin_dashboard')


# ==================== Rejected Messages Management ====================

@user_passes_test(is_admin_or_staff)
def view_rejected_view(request):
    rejected = Complaint.objects.filter(status='Rejected').order_by('-created_at')
    return render(request, 'SCMS/rejected_list.html', {'rejected': rejected})


@user_passes_test(is_admin_or_staff)
def delete_complaint_view_admin(request, pk):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk)
        complaint.delete()
        messages.success(request, "Complaint permanently deleted.")
    return redirect('view_rejected')