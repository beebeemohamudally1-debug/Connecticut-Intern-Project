# Login, recovery and status pages (frontend)

HTML, CSS and JS are finished for these screens. Backend: please do not change the templates; replace the stub views.

## Try it
```
python manage.py runserver
```
Open http://localhost:8000/preview (works only while `DEBUG = True`). It lists every screen and every state.
Add `?state=<name>` to any page URL to see one state, for example `/login?state=locked`.

## Files (all new, except one line in `config/urls.py`)
| Path | What |
|---|---|
| `templates/accounts/auth_base.html`, `auth_top.html` | The two layouts (navy panel + card, and top bar + card) |
| `templates/accounts/_auth_*.html` | Partials: field, alert, password rules, logo, icons |
| `templates/accounts/login.html` `forgot.html` `reset_verify.html` `reset_new.html` `reset_done.html` `admin_mfa.html` `admin_first_login.html` `provider_status.html` `home.html` `preview.html` | Screens |
| `static/accounts/css/auth.css`, `static/accounts/js/auth.js`, `static/accounts/img/home-service.jpg` | Styles, behaviour, photo. Every CSS class starts with `au-`, so nothing clashes with `style.css` or `admin.css` |
| `accounts/urls.py` | Routes, URL namespace `accounts` |
| `accounts/frontend_stubs.py` | Fake views + the state tables (the contract) |
| `accounts/auth_messages.py` | All copy, quoted from the lo-fi frames. Reuse it, do not retype text |
| `config/urls.py` | One line added at the end: `path('', include('accounts.urls'))` |

## Backend: how to take over
1. Copy each view from `frontend_stubs.py` into `accounts/views.py`, replace the body (each is marked `TODO(backend)`).
2. In `accounts/urls.py` change `from . import frontend_stubs as v` to `from . import views as v`.
3. Delete `frontend_stubs.py` and `preview.html` (and the `preview` route) when every state is reachable for real.
4. Set `LOGIN_URL = "accounts:login"` in settings.

## Routes
| URL | Name | Template |
|---|---|---|
| `/` | `accounts:home` | home.html |
| `/login` | `accounts:login` | login.html |
| `/logout` (POST) | `accounts:logout` | none |
| `/forgot-password` | `accounts:forgot_password` | forgot.html |
| `/forgot-password/verify` | `accounts:reset_verify` | reset_verify.html |
| `/forgot-password/new` | `accounts:reset_new` | reset_new.html |
| `/forgot-password/done` | `accounts:reset_done` | reset_done.html |
| `/provider/status` | `accounts:provider_status` | provider_status.html |
| `/admin-portal/login/mfa` | `accounts:admin_mfa` | admin_mfa.html |
| `/admin-portal/first-login` | `accounts:admin_first_login` | admin_first_login.html |

The site root `/` is the Welcome page (`accounts:home`). The project's links page (`config/views.py`) lives at `/dev/`.

The admin pages sit under `admin-portal/` (the project's admin area) because Django's own admin already owns `admin/`.
The login stub redirects to `dashboard:customer_dashboard`; the real view should route by role to
`dashboard:customer_dashboard`, `dashboard:handyman_dashboard` (active handyman), `accounts:provider_status`
(pending or rejected handyman) or `accounts:admin_mfa` (admin). Note that `role` here is `customer` / `handyman` / `admin`.
`templates/dashboard/customer_dashboard.html` does not exist yet.

## Context each template needs
- **Split pages** also take `panel`: `"login"` (tagline panel: login, S21, S22) or `"story"` (photo panel: S13 to S15).
- **login.html**: `email` (re-fill), `errors` dict (`email`, `password`), `alert` (one string), optional `title` ("Log in to admin account:" exists in the design).
- **forgot.html**: `errors` dict (`email`); after submit `submitted=True`, `email`, `notice`.
- **reset_verify.html**: `email`, `attempts_left`, `expires_in` (seconds left, 0 if expired), `cooldown` (seconds until resend), `state` (`wrong` / `expired` / `locked` / `hourly` or empty), `alert`, `notice`. POST: `code` (6 digits) or `action=resend`.
- **reset_new.html / admin_first_login.html**: `errors` dict (`password`, `confirm`), `rules` = list of `(key, label, met)` from `auth_messages.PW_RULES`. The page checks four rules live in JS; the server decides all five.
- **reset_done.html**: `message`. **admin_mfa.html**: `error`.
- **provider_status.html**: `display_name`, `email`, `account_status` (`PENDING_APPROVAL` / `REJECTED` / `ACTIVE`), `rejection_reason`.
- Top-bar pages use `request.user.is_authenticated` for Log in / Log out.

## States to reach for real (names match `?state=`)
**Login**: `empty`, `invalid`, `locked`, `suspended`, `disabled`, `rejected` (use the admin's real reason). Show suspended, disabled and rejected only after the password is verified.
**Verify**: `wrong`, `expired`, `locked`, `hourly`, `cooldown`. **New password**: `rules`, `mismatch`. **Admin MFA**: `wrong`. **Status**: `pending`, `rejected`, `active`.

## Design notes
- Values follow the front-end spec: navy #142D48, orange #F47939, 40px controls, 64px top bar, 8px radius, disabled = 50% opacity, breakpoints 768 / 1024.
- Contrast to watch: #C95050 error text and #718199 helper/placeholder text are close to or under 4.5:1 on white, and 50% opacity buttons reduce it further.
- S12 exists twice in the design ("Log in" and "Log in to admin account:"); the default is "Log in".
- S21 copy says both "email app" and "authenticator app"; authenticator app is used.
- Not built here: registration (S02 to S11), the admin application screens (S23, S24).

---

# Customer registration (S02 to S09)

Try it: `/register` is a clickable walk-through using a fake session. Every state is also at `/preview`.
Fake data to try: email `registered@example.com` = already registered; code `123456` = correct (anything else is wrong, 3 tries then locked); username `taken`, `admin` or `handyconnect` = taken.

## Files
| Path | What |
|---|---|
| `templates/accounts/register_base.html` | Layout: navy panel with vertical progress list, card on the right (slim bar + "Step X of 5" under 1024px) |
| `templates/accounts/register_role.html` `register_email.html` `register_confirm.html` `register_verify.html` `register_password.html` `register_expired.html` `register_customer.html` `register_done.html` | S02 to S09 |
| `templates/accounts/_reg_*.html` | Partials: field, select, textarea, role chip, progress list, icons |
| `static/accounts/css/register.css`, `static/accounts/js/register.js` | Styles (classes start `rg-`) and behaviour |
| `accounts/frontend_stubs_register.py` | Fake views, state tables (the contract) and reference validators |
| `accounts/auth_messages.py` | Registration copy added at the bottom (lines marked NEW are not in the design) |
| `accounts/urls.py` | Registration routes added |

Small fixes to the shared `static/accounts/css/auth.css` (3 rules at the end): button text no longer gets the form-label margin, primary button text is navy on orange (5.1:1; white would be 2.75:1), and the "Register" line under the login button has its spacing back.

## Routes
| URL | Name | Template |
|---|---|---|
| `/register` | `accounts:register` | register_role.html |
| `/register/email` | `register_email` | register_email.html |
| `/register/confirm-email` | `register_confirm` | register_confirm.html |
| `/register/verify` | `register_verify` | register_verify.html |
| `/register/password` | `register_password` | register_password.html |
| `/register/expired` | `register_expired` | register_expired.html |
| `/register/customer` | `register_customer` | register_customer.html |
| `/register/customer/done` | `register_done` | register_done.html |
| `/register/check-username` | `username_check` | JSON, see below |

## Context each template needs
All steps take `step` (1 Email, 2 Verify, 3 Password, 4 Details, 5 Done; 0 on S02 and S07), `role` (`customer`/`provider`) and `role_label` (the chip says "Chosen role: ...").
- **S02**: `role` (pre-select), `error`. POST `role`.
- **S03**: `email`, `errors.email`, `already_registered` (shows the "Log in" link). POST `email`.
- **S04**: `email`, `hint`. POST (no fields) sends the code.
- **S05**: `email`, `attempts_left`, `expires_in` (seconds, 0 if expired), `cooldown`, `state` (`wrong` / `expired` / `locked` / `hourly`), `alert`, `notice`. POST `code` or `action=resend`. Verify is disabled for `locked` and `expired`; Resend is disabled for `hourly`.
- **S06**: `errors.password`, `errors.confirm`, `rules` = `[(key, label, met)]`.
- **S07**: `message`. **S09**: `name`, `email`.
- **S08**: `email`, `values` {first_name, surname, additional_names, username, phone, region, address}, `regions` = `[(value, label)]` (nine), `errors` (same keys plus `terms`, `privacy`), `terms_accepted`, `privacy_accepted`. POST the fields plus `terms` and `privacy`.

## Live username check
JS calls `GET /register/check-username?username=abc` on blur. Return `200 {"available": true}`, `409 {"code": "USERNAME_TAKEN", "message": "...", "field": "username"}` or `400` when malformed. The server must still enforce uniqueness on submit.

## Decisions to know about
- S09 has "Go to login" (not a dashboard link): the requirements say users go to login after registering.
- Provider: the Service Provider card works on S02 and the flow runs to S06; S10 (provider details) is not built, so the stub sends providers home.
- Copy not in the design (marked NEW in `auth_messages.py`): account-type error, invalid-email text, "already registered" text, session-expired explanation, "new code sent".
- Region dropdown is a native `<select>`, so its open state is drawn by the browser.
- Terms and Privacy links are `#` placeholders until those pages exist.
- Helper text and error text on these pages use `#5A6A80` and `#B33D3D` (5.5:1 and 5.8:1) because the spec's `#718199` (3.96:1) and `#C95050` (4.42:1) fall just under AA.
