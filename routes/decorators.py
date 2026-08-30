from functools import wraps
from flask import session, redirect, url_for


# ==========================================================
# WORKER LOGIN REQUIRED
# ==========================================================

def worker_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        # Worker login check
        if session.get("role") != "worker":
            return redirect(
                url_for("auth.login", role="worker")
            )

        # user_id bhi available hona chahiye
        if not session.get("user_id"):
            session.clear()
            return redirect(
                url_for("auth.login", role="worker")
            )

        return view_function(*args, **kwargs)

    return wrapped_view


# ==========================================================
# PARTNER LOGIN REQUIRED
# ==========================================================

def partner_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        # Partner login check
        if session.get("role") != "partner":
            return redirect(
                url_for("auth.login", role="partner")
            )

        # user_id bhi available hona chahiye
        if not session.get("user_id"):
            session.clear()
            return redirect(
                url_for("auth.login", role="partner")
            )

        return view_function(*args, **kwargs)

    return wrapped_view


# ==========================================================
# ADMIN LOGIN REQUIRED
# ==========================================================

def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        # Admin login check
        if session.get("role") != "admin":
            return redirect("/admin/login")

        # Admin ID check
        if not session.get("admin_id"):
            session.clear()
            return redirect("/admin/login")

        return view_function(*args, **kwargs)

    return wrapped_view
