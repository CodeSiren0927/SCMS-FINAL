from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Complaint, StudentProfile


# Inline profile view so admins can edit School ID directly inside the User edit page
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "School Information"


# Extending the default User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (StudentProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_school_id",
        "get_course",
    )

    def get_school_id(self, obj):
        return obj.profile.school_id if hasattr(obj, "profile") else "-"

    get_school_id.short_description = "School ID"

    def get_course(self, obj):
        return (
            obj.profile.course_full_name if hasattr(obj, "profile") else "-"
        )

    get_course.short_description = "Course"


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Updated Complaint Admin
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    # CHANGED: 'id' was changed to 'pk' to properly reference Django's built-in primary key field
    list_display = (
        "pk",
        "title",
        "get_student_name",
        "get_school_id",
        "get_course",
        "category",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "category",
        "student__profile__course_full_name",
        "created_at",
    )

    # Allows admins to search complaints using Student ID, Name, or Course Name
    search_fields = (
        "title",
        "description",
        "student__username",
        "student__profile__school_id",
        "student__profile__course_full_name",
    )

    list_editable = ("status",)

    fieldsets = (
        ("Student Details", {"fields": ("student",)}),
        ("Complaint Overview", {"fields": ("title", "category", "description")}),
        ("Administrative Actions", {"fields": ("status", "admin_remarks")}),
    )

    readonly_fields = ("created_at", "updated_at")

    # Helper methods to fetch profile relations into columns
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    get_student_name.short_description = "Student Name"

    def get_school_id(self, obj):
        return (
            obj.student.profile.school_id
            if hasattr(obj.student, "profile")
            else "N/A"
        )

    get_school_id.short_description = "School ID"

    def get_course(self, obj):
        return (
            obj.student.profile.course_full_name
            if hasattr(obj.student, "profile")
            else "N/A"
        )

    get_course.short_description = "Course"