from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class BlockedUserMiddleware:
    """Logs out a user the moment an admin blocks them, even mid-session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, 'is_blocked', False):
            logout(request)
            messages.error(request, 'Your account has been blocked. Contact the school administrator.')
            return redirect('accounts:login')
        return self.get_response(request)
