"""
FRONTEND STUB VIEWS for registration (S02 to S11: customer and service provider).

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
from django.templatetags.static import static

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

# ---- Service provider registration (S10, S10b, S11) ------------------------------------------------------------------
PROVIDER_VALUES = {
    "first_name": "Jane", "surname": "Doe", "additional_names": "", "username": "jane_doe",
    "phone": "51234567", "address": "12 Royal Road, Port Louis",
}
PROVIDER_PICKS = {"selected_regions": ["Port Louis", "Moka"], "selected_categories": ["Plumbing", "Electrical"]}
PROVIDER = {  # S10. "selected" = Figma "Default with selections", "expanded" = "Expanded multiselects".
    "default": {},
    "selected": {"values": PROVIDER_VALUES, **PROVIDER_PICKS},
    "expanded": {"values": PROVIDER_VALUES, **PROVIDER_PICKS, "open_menus": True},
    "errors": {"errors": dict(M.PROVIDER_ERRORS), "values": {"phone": "5123", "username": "a!"}},
    "taken": {"errors": {"username": M.USERNAME_TAKEN}, "values": {**PROVIDER_VALUES, "username": "taken"}, **PROVIDER_PICKS},
    "no_selection": {"errors": {"regions": M.PROVIDER_ERRORS["regions"], "categories": M.PROVIDER_ERRORS["categories"]},
                     "values": PROVIDER_VALUES},
}
DEMO_IMAGE = "accounts/img/home-service.jpg"  # stands in for an uploaded photo in the demo states


def _uploaded():
    """Demo of files the server already holds (Figma "Uploaded files"). Real backend: only if you keep uploads between
    submits; each entry needs token (id of the stored file), name, type (JPEG or PNG), size (label) and url (to preview)."""
    url = static(DEMO_IMAGE)
    return {
        "id_photo": [{"token": "demo-id", "name": "id_card.jpg", "type": "JPEG", "size": "2.1 MB", "url": url}],
        "certificates": [
            {"token": "demo-cert-1", "name": "plumbing_certificate.png", "type": "PNG", "size": "1.4 MB", "url": url},
            {"token": "demo-cert-2", "name": "electrical_certificate.jpg", "type": "JPEG", "size": "1.8 MB", "url": url},
        ],
    }


DOCUMENTS = {  # S10b. "uploaded" = Figma "Uploaded files", "preview" = "Larger preview" (the page opens the ID preview).
    "default": {},
    "uploaded": {"uploaded": _uploaded, "terms_accepted": True, "privacy_accepted": True},
    "preview": {"uploaded": _uploaded, "terms_accepted": True, "privacy_accepted": True, "auto_preview": "id_photo"},
    "missing": {"errors": {"id_photo": M.DOC_ERRORS["id_photo"], "certificates": M.DOC_ERRORS["certificates"]}},
    "bad_file": {"errors": {"id_photo": f"id_card.pdf: {M.FILE_TYPE_ERROR}",
                            "certificates": f"scan_large.png: {M.FILE_SIZE_ERROR}"}},
    "failed": {"errors": {"certificates": M.FILE_UPLOAD_FAILED}},
    "terms": {"uploaded": _uploaded, "errors": {"terms": M.DOC_ERRORS["terms"], "privacy": M.DOC_ERRORS["privacy"]}},
}
FILE_RULES = {"types": ",".join(M.DOC_TYPES), "max_mb": M.DOC_MAX_MB, "type_error": M.FILE_TYPE_ERROR, "size_error": M.FILE_SIZE_ERROR}

# (title, url, table) rows added to the /preview gallery
PREVIEW_GROUPS = [
    ("S02 Choose account type", "/register", ROLE), ("S03 Email", "/register/email", EMAIL),
    ("S04 Confirm email", "/register/confirm-email", {"default": {}}),
    ("S05 Verify code", "/register/verify", VERIFY), ("S06 Create password", "/register/password", PASSWORD),
    ("S07 Session expired", "/register/expired", {"default": {}}),
    ("S08 Customer details", "/register/customer", DETAILS),
    ("S09 Account created", "/register/customer/done", {"default": {}}),
    ("S10 Provider details", "/register/provider", PROVIDER),
    ("S10b Provider documents", "/register/provider/documents", DOCUMENTS),
    ("S11 Application submitted", "/register/provider/done", {"default": {}}),
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
            # Customers continue to S08, service providers to S10.
            return redirect("accounts:register_customer" if _role(request)[0] == "customer" else "accounts:register_provider")
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


# --- S10 -------------------------------------------------------------------
def _provider_flow(request, step, **extra):
    """Same as _flow, but these pages always belong to the service provider path."""
    return {**_flow(request, step, **extra), "role": "provider", "role_label": M.ROLE_PROVIDER}


def register_provider(request):
    # TODO(backend): validate every field and keep the answers on the RegistrationSession (nothing is created yet);
    # the account is created in one transaction on S10b (FR-SPR-01..09, FR-SPR-19).
    ctx = {**_provider_flow(request, 4, part="Part 1 of 2", errors={}, values={}, regions=M.REGIONS, categories=M.SERVICE_CATEGORIES,
                            selected_regions=[], selected_categories=[]), **_pick(request, PROVIDER)}
    if request.method == "POST":
        values = {k: request.POST.get(k, "").strip() for k in PROVIDER_VALUES}
        regions, categories = request.POST.getlist("regions"), request.POST.getlist("categories")
        errors = validate_provider(values, regions, categories)
        ctx.update(values=values, errors=errors, selected_regions=regions, selected_categories=categories)
        if not errors:
            request.session["reg_provider"] = {**values, "regions": regions, "categories": categories}
            return redirect("accounts:register_provider_documents")
    return render(request, "accounts/register_provider.html", ctx)


# --- S10b ------------------------------------------------------------------
def register_provider_documents(request):
    # TODO(backend): if the RegistrationSession has no S10 answers, redirect to accounts:register_expired. On POST check
    # every file (JPEG/PNG, max 5 MB, FR-SPR-16), then in ONE transaction create the account with status PENDING_APPROVAL,
    # store each document linked to it and record consent (FR-SPR-10, 14, 15, 19). If any upload fails create nothing.
    details = request.session.get("reg_provider") or PROVIDER_VALUES
    name = f"{details['first_name']} {details['surname']}"
    ctx = {**_provider_flow(request, 4, part="Part 2 of 2", errors={}, name=name, file_rules=FILE_RULES, uploaded={}),
           **_pick(request, DOCUMENTS)}
    if callable(ctx.get("uploaded")):
        ctx["uploaded"] = ctx["uploaded"]()
    if request.method == "POST":
        errors = validate_documents(request)
        ctx.update(errors=errors, terms_accepted=bool(request.POST.get("terms")), privacy_accepted=bool(request.POST.get("privacy")))
        if not errors:
            request.session["reg_name"] = name
            return redirect("accounts:register_provider_done")
    return render(request, "accounts/register_provider_documents.html", ctx)


# --- S11 -------------------------------------------------------------------
def register_provider_done(request):
    # TODO(backend): show the new account's name. The account is Pending Approval; no auto-login, the provider goes to login (FR-ACC-13).
    return render(request, "accounts/register_provider_done.html", {
        "step": 5, "role": "provider", "role_label": M.ROLE_PROVIDER,
        "name": request.session.get("reg_name", "Jane Doe"), "email": request.session.get("reg_email", "jane@example.com"),
    })


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


def validate_provider(values, regions, categories):
    """Field errors for the provider details form. Names, username, phone and address follow the customer rules."""
    errors = validate_customer({**values, "region": M.REGIONS[0][0]}, True, True)  # region, terms, privacy do not apply here
    if not regions or not set(regions) <= {v for v, _ in M.REGIONS}:
        errors["regions"] = M.PROVIDER_ERRORS["regions"]
    if not categories or not set(categories) <= {v for v, _ in M.SERVICE_CATEGORIES}:
        errors["categories"] = M.PROVIDER_ERRORS["categories"]
    return errors


def validate_documents(request):
    """Errors for the documents form. Files: JPEG or PNG, at most 5 MB each (FR-SPR-14..16).
    keep_id_photo / keep_certificates carry the tokens of files the server already holds (only if you keep uploads)."""
    def bad(f):
        if f.content_type not in M.DOC_TYPES:
            return f"{f.name}: {M.FILE_TYPE_ERROR}"
        if f.size > M.DOC_MAX_MB * 1024 * 1024:
            return f"{f.name}: {M.FILE_SIZE_ERROR}"
        return ""

    errors = {}
    id_file, certs = request.FILES.get("id_photo"), request.FILES.getlist("certificates")
    if id_file:
        if bad(id_file):
            errors["id_photo"] = bad(id_file)
    elif not request.POST.get("keep_id_photo"):
        errors["id_photo"] = M.DOC_ERRORS["id_photo"]
    cert_errors = [m for m in map(bad, certs) if m]
    if cert_errors:
        errors["certificates"] = " ".join(cert_errors)
    elif not certs and not request.POST.getlist("keep_certificates"):
        errors["certificates"] = M.DOC_ERRORS["certificates"]
    if not request.POST.get("terms"):
        errors["terms"] = M.DOC_ERRORS["terms"]
    if not request.POST.get("privacy"):
        errors["privacy"] = M.DOC_ERRORS["privacy"]
    return errors
