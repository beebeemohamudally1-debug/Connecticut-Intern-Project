"""
FRONTEND STUB VIEWS for the login, recovery, admin sign-in and status pages.

Every view renders a finished template with fake context so each screen state can be seen
without a backend. Add ?state=<name> to a GET URL to preview a state (see /preview).

BACKEND DEVELOPER: copy each view into accounts/views.py, replace the body, and keep the template
names, URL names and context keys listed in FRONTEND_AUTH_README.md. Then change the import in
accounts/urls.py from `frontend_stubs` to `views`, and delete this file.
"""
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from . import auth_messages as M
from django.contrib.auth import authenticate, login
from django.contrib import messages

RULES_UNMET = [(k, label, False) for k, label in M.PW_RULES]
RULES_MET = [(k, label, True) for k, label in M.PW_RULES]
REASON = "The submitted ID photo is unreadable. Please provide a clear photo."
SAMPLE_EMAIL = "sample.user@example.com"
PERSON = {"display_name": "Sample User", "email": SAMPLE_EMAIL}

# state name -> context. This is the CONTRACT: the real views must produce the same keys.
LOGIN = {
    "default": {},
    "empty": {"errors": {"email": M.EMAIL_REQUIRED, "password": M.PASSWORD_REQUIRED}},
    "invalid": {"email": SAMPLE_EMAIL, "alert": M.INVALID_CREDENTIALS},
    "locked": {"email": SAMPLE_EMAIL, "alert": M.LOCKED},
    "suspended": {"email": SAMPLE_EMAIL, "alert": M.SUSPENDED},
    "disabled": {"email": SAMPLE_EMAIL, "alert": M.DISABLED},
    "rejected": {"email": SAMPLE_EMAIL, "alert": M.REJECTED.format(reason=REASON)},
    "admin-title": {"title": "Log in to admin account:"},
}
FORGOT = {
    "default": {},
    "empty": {"errors": {"email": M.EMAIL_REQUIRED}},
    "submitted": {"submitted": True, "email": SAMPLE_EMAIL, "notice": M.FORGOT_GENERIC},
}
VERIFY_BASE = {"email": SAMPLE_EMAIL, "attempts_left": 3, "expires_in": 300, "cooldown": 0}
VERIFY = {
    "default": {},
    "wrong": {"alert": M.CODE_WRONG, "attempts_left": 2, "state": "wrong"},
    "expired": {"alert": M.CODE_EXPIRED, "expires_in": 0, "state": "expired"},
    "locked": {"alert": M.CODE_LOCKED, "attempts_left": 0, "state": "locked"},
    "hourly": {"alert": M.CODE_HOURLY, "state": "hourly"},
    "cooldown": {"cooldown": 45},
}
NEW = {
    "default": {"rules": RULES_UNMET},
    "rules": {"rules": RULES_UNMET, "errors": {"password": M.RESET_RULES_UNMET}},
    "mismatch": {"rules": RULES_MET, "errors": {"confirm": M.RESET_MISMATCH}},
}
MFA = {"default": {}, "wrong": {"error": M.ADMIN_CODE_WRONG}}
STATUS = {
    "pending": {"account_status": "PENDING_APPROVAL"},
    "rejected": {"account_status": "REJECTED", "rejection_reason": REASON},
    "active": {"account_status": "ACTIVE"},
}


def _pick(request, table, default="default"):
    """Context for the ?state= named in the URL (falls back to the default state)."""
    return dict(table.get(request.GET.get("state", default), table[default]))


def home(request):
    return render(request, "accounts/home.html")




def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            user = authenticate(
                request,
                username=user.username,
                password=password
            )

        if user is not None and user.is_active:
            login(request, user)

            if user.is_superuser or user.role == "admin":
                return redirect("dashboard:admin_dashboard")

            if user.role == "handyman":
                return redirect("dashboard:handyman_dashboard")

            return redirect("dashboard:customer_dashboard")

        messages.error(request, "Invalid email or password.")

    return render(
        request,
        "accounts/login.html",
        {
            "errors": {},
            "email": "",
            "panel": "login",
            **_pick(request, LOGIN)
        }
    )




def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def forgot_password(request):
    # TODO(backend): same neutral result whether or not the email exists; send a code only if eligible.
    ctx = {"errors": {}, "email": "", "panel": "story"}
    if request.method == "POST":  # stub: show the "submitted" state
        ctx.update(FORGOT["submitted"])
    else:
        ctx.update(_pick(request, FORGOT))
    return render(request, "accounts/forgot.html", ctx)


def reset_verify(request):
    # TODO(backend): resend (POST action=resend) and code check (POST code=123456).
    if request.method == "POST" and request.POST.get("action") != "resend":
        return redirect("accounts:reset_new")  # stub
    return render(request, "accounts/reset_verify.html", {"panel": "story", **VERIFY_BASE, **_pick(request, VERIFY)})


def reset_new(request):
    # TODO(backend): validate rules + match, set password, delete other sessions, send "password changed" email.
    if request.method == "POST":
        return redirect("accounts:reset_done")  # stub
    return render(request, "accounts/reset_new.html", {"errors": {}, "panel": "story", **_pick(request, NEW)})


def reset_done(request):
    return render(request, "accounts/reset_done.html", {"panel": "story", "message": M.RESET_DONE})


def admin_mfa(request):
    # TODO(backend): verify the TOTP code (django-otp), then go to first-login or the admin dashboard.
    if request.method == "POST":
        return redirect("accounts:admin_first_login")  # stub
    return render(request, "accounts/admin_mfa.html", {"panel": "login", **_pick(request, MFA)})


def admin_first_login(request):
    # TODO(backend): enforce must_change_password, validate rules + match, then continue to the admin dashboard.
    if request.method == "POST":
        return redirect("accounts:login")  # stub
    return render(request, "accounts/admin_first_login.html", {"errors": {}, "panel": "login", **_pick(request, NEW)})


def provider_status(request):
    # TODO(backend): login required + handyman role; show the real status and rejection_reason.
    return render(request, "accounts/provider_status.html", {**PERSON, **_pick(request, STATUS, "pending")})


def preview_index(request):
    """Dev-only gallery of every screen state. Only works while DEBUG is on. Delete with this file."""
    if not settings.DEBUG:
        raise Http404
    groups = [
        ("S12 Login", "/login", LOGIN), ("S13 Forgot password", "/forgot-password", FORGOT),
        ("S14 Reset verification", "/forgot-password/verify", VERIFY), ("S15 New password", "/forgot-password/new", NEW),
        ("S18 Application status", "/provider/status", STATUS), ("S21 Admin MFA", "/admin-portal/login/mfa", MFA),
        ("S22 Admin first login", "/admin-portal/first-login", NEW),
    ]
    rows = [(t, [(s, f"{u}?state={s}") for s in tbl]) for t, u, tbl in groups]
    rows.append(("Other", [("S01 Home", "/"), ("S15 Success", "/forgot-password/done")]))
    return render(request, "accounts/preview.html", {"rows": rows})
