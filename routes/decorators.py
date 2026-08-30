from functools import wraps
from flask import session, redirect, url_for


# ==========================================================
# WORKER LOGIN REQUIRED
# ==========================================================

def worker_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if session.get("role") != "worker":
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# ==========================================================
# PARTNER LOGIN REQUIRED
# ==========================================================

def partner_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if session.get("role") != "partner":
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# ==========================================================
# ADMIN LOGIN REQUIRED
# ==========================================================

def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if session.get("role") != "admin":
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapped_view
