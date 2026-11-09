from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from .forms import LoginForm


class UserLoginView(LoginView):
    """
    Renders login template and authenticates user.
    Redirects authenticated users to the dashboard.
    """
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class UserLogoutView(View):
    """
    Logs out user and redirects to login page.
    Supports both GET and POST requests cleanly.
    """
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been successfully logged out.")
        return redirect('login')

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been successfully logged out.")
        return redirect('login')
