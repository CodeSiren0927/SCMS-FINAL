from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ("Academic", "Academic Issues (Grades, Faculty, Schedule)"),
        ("Facilities", "Facilities & Infrastructure (Classrooms, Labs, Restrooms)"),
        ("Administrative", "Administrative Services (Registrar, Finance, Billing)"),
        ("Student Affairs", "Student Services & Organizations"),
        ("Others", "Other General Miscellaneous Inquiries"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Resolved", "Resolved"),
        ("Rejected", "Rejected"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    title = models.CharField(max_length=200, verbose_name="Complaint Title")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Others")
    description = models.TextField(verbose_name="Detailed Description")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    viewed = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True, verbose_name="Admin Remarks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.student.username} ({self.status})"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    school_id = models.CharField(max_length=20, unique=True, null=True, blank=True,
                                 verbose_name="School ID / Student ID")
    course_full_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Course Full Name")

    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.school_id or 'No ID Assigned'})"


# --- UPDATED NOTIFICATION MODEL ---
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    status = models.CharField(max_length=20, default="Pending")  # <-- Added field to prevent TypeErrors and handle dynamic UI colors
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}..."


# ==================== SIGNALS ====================

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


# --- UPDATED: AUTOMATED STATUS CHANGE NOTIFICATION SIGNAL ---
@receiver(post_save, sender=Complaint)
def notify_student_on_status_change(sender, instance, created, **kwargs):
    """
    Triggers an in-app notification record whenever an admin updates
    the status of a student's complaint.
    """
    if not created:
        status_display = instance.get_status_display()

        if instance.status == "Rejected":
            reason = instance.admin_remarks if instance.admin_remarks else "No remarks provided by administration."
            notification_message = f"Your complaint '{instance.title}' was rejected. Reason: {reason}"
        elif instance.status == "Resolved":
            remarks = f" Remarks: {instance.admin_remarks}" if instance.admin_remarks else ""
            notification_message = f"Great news! Your complaint '{instance.title}' has been marked as Resolved.{remarks}"
        else:
            notification_message = f"The status of your complaint '{instance.title}' has been updated to: {status_display}."

        # Create and commit the persistent notification instance into the database
        Notification.objects.create(
            user=instance.student,
            complaint=instance,
            message=notification_message,
            status=instance.status  # <-- Included tracking state synchronization
        )