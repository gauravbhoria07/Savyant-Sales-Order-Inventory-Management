from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from rest_framework import permissions


def admin_required(view_func):
    """
    Decorator for views that checks whether the logged-in user has the ADMIN role.
    If not, raises PermissionDenied or redirects with a helpful warning message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin:
            messages.error(request, "Access denied. Admin privileges are required for this action.")
            raise PermissionDenied("Admin privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class IsAdminUserRole(permissions.BasePermission):
    """
    DRF permission class: Allows access only to authenticated Admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsSalesUserRole(permissions.BasePermission):
    """
    DRF permission class: Allows access only to authenticated Sales Users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_sales_user)
