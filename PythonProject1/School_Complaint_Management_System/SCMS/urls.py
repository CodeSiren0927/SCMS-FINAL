from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='root_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Student Routes
    path('submit_complaint/', views.submit_complaint_view, name='submit_complaint'),
    path('profile/', views.profile_view, name='profile'),
    path('notification/delete/<int:pk>/', views.delete_notification_view, name='delete_notification'),

    # Student Modification Routes
    path('complaint/edit/<int:pk>/', views.edit_complaint_view, name='edit_complaint'),
    path('complaint/delete/<int:pk>/', views.delete_complaint_view, name='delete_complaint'),

    # Admin Dashboard Routes
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/complaint/<int:pk>/', views.complaint_detail_view, name='complaint_detail'),
    path('admin-dashboard/complaint/<int:pk>/update/', views.update_complaint_status_view, name='update_status'),

    # Admin Rejected Management
    path('admin-dashboard/rejected/', views.view_rejected_view, name='view_rejected'),
    path('admin-dashboard/delete/<int:pk>/', views.delete_complaint_view_admin, name='delete_complaint_admin'),
]