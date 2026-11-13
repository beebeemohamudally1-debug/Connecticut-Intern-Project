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
