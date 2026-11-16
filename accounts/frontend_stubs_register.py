"""
FRONTEND STUB VIEWS for customer registration (S02 to S09).

Like frontend_stubs.py, these render finished templates with fake data so every state can be seen
without a backend (add ?state=<name> to a GET URL; see /preview). Unlike the login stubs they also
walk the real flow with a tiny session-based fake, so you can click through S02 -> S09:

    email "registered@example.com"        -> "already registered" state
    code 123456                            -> correct code; anything else -> wrong code (3 tries, then locked)
    username taken / admin / handyconnect  -> "This username is already taken."

BACKEND DEVELOPER: copy each view into accounts/views.py, replace the body, keep the template names, URL names and
context keys documented in FRONTEND_AUTH_README.md, then change the import in accounts/urls.py and delete this file.
The validators at the bottom mirror the rules in the functional requirements; reuse or replace them in a real Form.
"""
import re

from django.http import JsonResponse
from django.shortcuts import redirect, render

from . import auth_messages as M

SAMPLE_EMAIL = "sample.user@example.com"
RULES_UNMET = [(k, label, False) for k, label in M.PW_RULES]
RULES_MET = [(k, label, True) for k, label in M.PW_RULES]
TAKEN_USERNAMES = {"taken", "admin", "handyconnect"}
REGISTERED_EMAILS = {"registered@example.com"}
GOOD_CODE = "123456"

# state name -> context. This is the CONTRACT: the real views must produce the same keys.
ROLE = {
    "default": {},
    "customer": {"role": "customer"},
    "provider": {"role": "provider"},
    "error": {"error": M.ROLE_REQUIRED},
}
EMAIL = {
    "default": {},
    "empty": {"errors": {"email": M.EMAIL_REQUIRED}},
    "invalid": {"email": "jane@example", "errors": {"email": M.REG_EMAIL_INVALID}},
    "registered": {"email": "registered@example.com", "errors": {"email": M.REG_EMAIL_TAKEN}, "already_registered": True},
}
VERIFY_BASE = {"email": SAMPLE_EMAIL, "attempts_left": 3, "expires_in": 300, "cooldown": 0}
VERIFY = {
    "default": {},
    "wrong": {"alert": M.REG_CODE_WRONG, "attempts_left": 2, "state": "wrong"},
    "expired": {"alert": M.REG_CODE_EXPIRED, "expires_in": 0, "state": "expired"},
    "locked": {"alert": M.REG_CODE_LOCKED, "attempts_left": 0, "state": "locked"},
    "hourly": {"alert": M.REG_CODE_HOURLY, "state": "hourly"},
    "cooldown": {"cooldown": 45},
    "resent": {"notice": M.REG_CODE_SENT, "cooldown": 60},
}
PASSWORD = {
    "default": {"rules": RULES_UNMET},
    "rules": {"rules": RULES_UNMET, "errors": {"password": M.REG_PW_UNMET}},
    "mismatch": {"rules": RULES_MET, "errors": {"confirm": M.REG_PW_MISMATCH}},
}
SAMPLE_VALUES = {
    "first_name": "Sample", "surname": "User", "additional_names": "", "username": "sample_user",
    "phone": "51234567", "region": "Moka", "address": "12 Example Street, Moka",
}
DETAILS = {
    "default": {},
    "errors": {"errors": dict(M.CUSTOMER_ERRORS), "values": {"phone": "5123", "username": "a!"}},
    "taken": {"errors": {"username": M.USERNAME_TAKEN}, "values": {**SAMPLE_VALUES, "username": "taken"},
              "terms_accepted": True, "privacy_accepted": True},
    "terms": {"errors": {"terms": M.CUSTOMER_ERRORS["terms"], "privacy": M.CUSTOMER_ERRORS["privacy"]},
              "values": SAMPLE_VALUES},
    "filled": {"values": SAMPLE_VALUES, "terms_accepted": True, "privacy_accepted": True},
}

# (title, url, table) rows added to the /preview gallery
PREVIEW_GROUPS = [
    ("S02 Choose account type", "/register", ROLE), ("S03 Email", "/register/email", EMAIL),
    ("S04 Confirm email", "/register/confirm-email", {"default": {}}),
    ("S05 Verify code", "/register/verify", VERIFY), ("S06 Create password", "/register/password", PASSWORD),
    ("S07 Session expired", "/register/expired", {"default": {}}),
    ("S08 Customer details", "/register/customer", DETAILS),
    ("S09 Account created", "/register/customer/done", {"default": {}}),
]


def _pick(request, table, default="default"):
    """Context for the ?state= named in the URL (falls back to the default state)."""
    return dict(table.get(request.GET.get("state", default), table[default]))


def _role(request):
    """Chosen role, remembered between steps. Backend: keep it on the server-side RegistrationSession."""
    role = request.session.get("reg_role") or request.GET.get("role") or "customer"
    return role, (M.ROLE_PROVIDER if role == "provider" else M.ROLE_CUSTOMER)


def _flow(request, step, **extra):
    """Context shared by every registration page: step number (1 to 5) and the chosen role."""
    role, label = _role(request)
    return {"step": step, "role": role, "role_label": label, "email": request.session.get("reg_email", SAMPLE_EMAIL), **extra}


# --- S02 -------------------------------------------------------------------
def register_role(request):
    # TODO(backend): store the chosen role on the RegistrationSession (FR-REG-02/03).
    if request.method == "POST":
        role = request.POST.get("role")
        if role not in ("customer", "provider"):
            return render(request, "accounts/register_role.html", {"step": 0, "error": M.ROLE_REQUIRED})
        request.session["reg_role"] = role
        return redirect("accounts:register_email")
    ctx = {"step": 0, **_pick(request, ROLE)}
    if "role" not in ctx and request.session.get("reg_role"):
        ctx["role"] = request.session["reg_role"]
    return render(request, "accounts/register_role.html", ctx)


# --- S03 -------------------------------------------------------------------
def register_email(request):
    # TODO(backend): trim + lowercase, validate format, reject existing accounts, rate-limit this check (FR-REG-04..06).
    ctx = {**_flow(request, 1, errors={}), **_pick(request, EMAIL)}
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        ctx["email"] = email
        if not email:
            ctx["errors"] = {"email": M.EMAIL_REQUIRED}
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            ctx["errors"] = {"email": M.REG_EMAIL_INVALID}
        elif email in REGISTERED_EMAILS:
            ctx.update(errors={"email": M.REG_EMAIL_TAKEN}, already_registered=True)
        else:
            request.session["reg_email"] = email
            return redirect("accounts:register_confirm")
    elif "email" not in request.GET and not request.GET.get("state"):
        ctx["email"] = request.session.get("reg_email", "")
    return render(request, "accounts/register_email.html", ctx)


# --- S04 -------------------------------------------------------------------
def register_confirm(request):
    # TODO(backend): POST = generate + email the code (FR-REG-07/08), then go to the verify page.
    if request.method == "POST":
        request.session["reg_attempts"] = 3
        request.session["reg_codes"] = 1
        return redirect("accounts:register_verify")
    return render(request, "accounts/register_confirm.html", _flow(request, 1, hint=M.REG_CONFIRM_HINT))


# --- S05 -------------------------------------------------------------------
def register_verify(request):
    # TODO(backend): POST code=123456 to check, or action=resend. Rules: 300 s expiry, 3 attempts, 60 s cooldown, 5 codes/hour.
    ctx = {**_flow(request, 2), **{k: v for k, v in VERIFY_BASE.items() if k != "email"}, **_pick(request, VERIFY)}
    if request.method == "POST":
        if request.POST.get("action") == "resend":
            codes = request.session.get("reg_codes", 1) + 1
            request.session["reg_codes"] = codes
            if codes > 5:
                ctx.update(VERIFY["hourly"])
            else:
                request.session["reg_attempts"] = 3
                ctx.update(VERIFY["resent"])
        else:
            left = request.session.get("reg_attempts", 3)
            if request.POST.get("code") == GOOD_CODE and left > 0:
                return redirect("accounts:register_password")
            left = max(left - 1, 0)
            request.session["reg_attempts"] = left
            ctx.update(VERIFY["locked"] if left == 0 else {**VERIFY["wrong"], "attempts_left": left})
    return render(request, "accounts/register_verify.html", ctx)


# --- S06 -------------------------------------------------------------------
def register_password(request):
    # TODO(backend): validate the five rules + match on the server, keep the hash on the RegistrationSession (FR-ACC-01..07).
    ctx = {**_flow(request, 3, errors={}), **_pick(request, PASSWORD)}
    if request.method == "POST":
        password, confirm = request.POST.get("password", ""), request.POST.get("confirm", "")
        rules = password_rules(password)
        ctx["rules"] = rules
        if not all(met for _, _, met in rules):
            ctx["errors"] = {"password": M.REG_PW_UNMET}
        elif password != confirm:
            ctx["errors"] = {"confirm": M.REG_PW_MISMATCH}
        else:
            # Providers continue to S10 (provider details), which is not built yet.
            return redirect("accounts:register_customer" if _role(request)[0] == "customer" else "accounts:home")
    return render(request, "accounts/register_password.html", ctx)


# --- S07 -------------------------------------------------------------------
def register_expired(request):
    return render(request, "accounts/register_expired.html", {"step": 0, "message": M.REG_SESSION_EXPIRED})


# --- S08 -------------------------------------------------------------------
def register_customer(request):
    # TODO(backend): validate every field, enforce the case-insensitive unique username in the DB, create the account atomically (FR-CUS-01..08).
    ctx = {**_flow(request, 4, errors={}, values={}, regions=M.REGIONS), **_pick(request, DETAILS)}
    if request.method == "POST":
        values = {k: request.POST.get(k, "").strip() for k in SAMPLE_VALUES}
        errors = validate_customer(values, request.POST.get("terms"), request.POST.get("privacy"))
        ctx.update(values=values, errors=errors, terms_accepted=bool(request.POST.get("terms")),
                   privacy_accepted=bool(request.POST.get("privacy")))
        if not errors:
            request.session["reg_name"] = f"{values['first_name']} {values['surname']}"
            return redirect("accounts:register_done")
    return render(request, "accounts/register_customer.html", ctx)


# --- S09 -------------------------------------------------------------------
def register_done(request):
    # TODO(backend): show the new account's name. Design decision: no auto-login, the user goes to the login page.
    name = request.session.get("reg_name", "Sample Customer")
    return render(request, "accounts/register_done.html", {"step": 5, "name": name, "email": request.session.get("reg_email", SAMPLE_EMAIL)})


# --- live username check (HTMX/fetch) ---------------------------------------
def username_check(request):
    """GET ?username=abc. 200 {"available": true}, or 409 {"code", "message", "field"} when taken, 400 when malformed."""
    username = request.GET.get("username", "").strip()
    if not re.fullmatch(r"\w{3,30}", username, re.ASCII):
        return JsonResponse({"code": "USERNAME_INVALID", "message": M.CUSTOMER_ERRORS["username"], "field": "username"}, status=400)
    if username.lower() in TAKEN_USERNAMES:
        return JsonResponse({"code": "USERNAME_TAKEN", "message": M.USERNAME_TAKEN, "field": "username"}, status=409)
    return JsonResponse({"available": True})


# --- validators (reference for the real Forms) -------------------------------
def password_rules(password):
    """[(key, label, met)] for the five password rules. The common list here is tiny; the backend uses Django's."""
    met = {
        "len": len(password) >= 8, "upper": bool(re.search(r"[A-Z]", password)),
        "lower": bool(re.search(r"[a-z]", password)), "digit": bool(re.search(r"\d", password)),
        "common": password.lower() not in {"password", "password1", "12345678", "qwerty123", "letmein123"},
    }
    return [(k, label, met[k]) for k, label in M.PW_RULES]


def validate_customer(values, terms, privacy):
    """Field errors for the customer details form (copy from auth_messages.CUSTOMER_ERRORS)."""
    e = M.CUSTOMER_ERRORS
    name_ok = lambda s: bool(re.fullmatch(r"[^\W\d_][\w' .-]*", s, re.UNICODE)) and not re.search(r"[\d_]", s)  # noqa: E731
    errors = {}
    if not name_ok(values["first_name"]):
        errors["first_name"] = e["first_name"]
    if not name_ok(values["surname"]):
        errors["surname"] = e["surname"]
    if values["additional_names"] and not name_ok(values["additional_names"]):
        errors["additional_names"] = e["additional_names"]
    if not re.fullmatch(r"\w{3,30}", values["username"], re.ASCII):
        errors["username"] = e["username"]
    elif values["username"].lower() in TAKEN_USERNAMES:
        errors["username"] = M.USERNAME_TAKEN
    if not re.fullmatch(r"\d{8}", values["phone"], re.ASCII):
        errors["phone"] = e["phone"]
    if values["region"] not in dict(M.REGIONS):
        errors["region"] = e["region"]
    if not values["address"]:
        errors["address"] = e["address"]
    if not terms:
        errors["terms"] = e["terms"]
    if not privacy:
        errors["privacy"] = e["privacy"]
    return errors
