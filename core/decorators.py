from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def profile_required(view):
    """Logged-in user with a Lafiya profile; the profile is passed to the view."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            messages.info(request, "Please complete your Lafiya profile first.")
            return redirect("profile_setup")
        return view(request, profile, *args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(view):
        @profile_required
        @wraps(view)
        def wrapper(request, profile, *args, **kwargs):
            if profile.role not in roles and not request.user.is_superuser:
                messages.warning(request, "That page is for health workers and government partners.")
                return redirect("home")
            return view(request, profile, *args, **kwargs)

        return wrapper

    return decorator
