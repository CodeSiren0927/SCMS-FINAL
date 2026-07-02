from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile

class StudentRegistrationForm(UserCreationForm):
    school_id = forms.CharField(max_length=20, required=False)
    course_full_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, created = StudentProfile.objects.get_or_create(user=user)
        profile.school_id = self.cleaned_data.get('school_id')
        profile.course_full_name = self.cleaned_data.get('course_full_name')
        if commit:
            profile.save()
        return user