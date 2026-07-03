from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='root_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Authentication Extension Routes
    path('password-reset/request/', views.request_password_reset_view, name='request_password_reset'),

    # Student Routes
    path('submit_complaint/', views.submit_complaint_view, name='submit_complaint'),
    path('profile/', views.profile_view, name='profile'),
    path('notification/delete/<int:pk>/', views.delete_notification_view, name='delete_notification'),
    path('account/delete/', views.delete_account_view, name='delete_account'),

    # Student Modification Routes
    path('complaint/edit/<int:pk>/', views.edit_complaint_view, name='edit_complaint'),
    path('complaint/delete/<int:pk>/', views.delete_complaint_view, name='delete_complaint'),

    # Admin Dashboard Routes
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),

    # FIX 1: Aligned to match your panel link -> name='complaint_detail'
    path('admin-dashboard/complaint/<int:pk>/', views.complaint_detail_view, name='complaint_detail'),
    path('admin-dashboard/complaint/<int:pk>/update/', views.update_complaint_status_view, name='update_status'),

    # Admin Security Control Routes
    path('admin-dashboard/password-reset/confirm/<int:pk>/', views.confirm_password_reset_view,
         name='confirm_password_reset'),

    # FIX 2: Aligned to match the AJAX fetch address format -> /admin/users/restrict/<id>/
    path('admin/users/restrict/<int:user_id>/', views.restrict_user_complaints_view,
         name='restrict_user_complaints'),

    # Admin Rejected Management
    path('admin-dashboard/rejected/', views.view_rejected_view, name='view_rejected'),
    path('admin-dashboard/delete/<int:pk>/', views.delete_complaint_view_admin, name='delete_complaint_admin'),
]