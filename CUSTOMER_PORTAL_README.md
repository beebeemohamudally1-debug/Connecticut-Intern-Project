# Customer portal frontend: handoff notes

Frontend only (HTML, CSS, JS). Built from the Figma "Customer · …" frames. Every page renders with **no context at all** (empty states) so nothing crashes before the backend exists; each template has a `{% comment %}` header listing the context and POST fields it expects.

## What changed

**Replaced in place** (existing context variables, URL names and POST field names kept):
`templates/base_customer.html`, `templates/jobs/base_user.html` (customer branch only; handyman layout is untouched),
`templates/payments/` → `my_quotations`, `quotation_detail`, `payment_history`, `customer_invoice`, `customer_invoice_list`, `customer_inspection_fee`, `customer_receipt`, `customer_history`, `customer_penalties`,
`templates/reviews/` → `my_reviews`, `submit_review`,
`templates/dashboard/customer_dashboard.html` (new file; the view already pointed at it),
shared templates `complaints/complaint_{list,form,detail}.html` and `jobs/job_{list,detail}.html`: wrapped as `{% if role == 'customer' %}{% include "customer/_….html" %}{% else %}…original admin/handyman markup…{% endif %}`. Admin and handyman pages render exactly as before.

**New**: `static/customer/css/customer.css` (all classes `cp-…`, scoped under `.cp`), `static/customer/js/customer.js`, `templates/customer/*` (shell, icons, badge, new_request, request_submitted, requests, appointments, notifications, profile, history, `_complaint_*`, `_job_*`), public page `templates/services/service_results.html` + `static/services/css/results.css`, and `templates/accounts/_public_{sprite,nav,foot}.html` (copied from the landing page).

Not touched: admin-only `reports/job_summary.html` (the Figma "Print · Job summary" frame), all admin and handyman templates.

## URL names the templates look up (all optional)
Sidebar and buttons use `{% url 'name' as var %}`, so a missing route becomes `#` instead of an error. These routes now exist: the `customer_portal` Django app (mounted at `/customer/`) provides them, with views reading real data. The public results page is `services:results` (`/services/results/`).

| name | page | template |
|---|---|---|
| `customer_portal:new_request` | New service request (POST here) | `customer/new_request.html` |
| `customer_portal:request_submitted` | Confirmation after POST | `customer/request_submitted.html` |
| `customer_portal:requests` | My requests | `customer/requests.html` |
| `customer_portal:appointments` | Appointments | `customer/appointments.html` |
| `customer_portal:notifications`, `…:notifications_read_all` (POST) | Notifications | `customer/notifications.html` |
| `customer_portal:profile` | Profile & security (3 forms via hidden `action`) | `customer/profile.html` |
| `customer_portal:history` | History | `customer/history.html` |
| `services:results` | Public service results (GET filters) | `services/service_results.html` |

Existing routes used: `dashboard:customer_dashboard`, `payments:*`, `reviews:my_reviews`, `reviews:submit_review`, `complaints:*`, `jobs:list/detail/evidence_file`, `services:search`, `accounts:logout/register/home`.

## Backend to-dos the design implies (nothing here blocks rendering)
- **Dashboard context**: `first_name, active_count, quote_ready_count, upcoming_count, next_visit, completed_count, feedback_count, recent_requests, updates, next_appointment, unread_count`. Add `unread_count` to a context processor and the sidebar and bell badges work on every page.
- **New request form** posts fields that have no column yet: `title`, `service_type`, `access_notes`, `attachments`. The rest map to `ServiceRequest` (`service_category`, `problem_description`, `service_address`, `contact_name`, `contact_phone`, `preferred_date`, `preferred_slot`).
- **Complaint form**: the design also shows category, incident date, preferred outcome and a confirm checkbox. They render automatically if `ComplaintForm` gains fields named `category`, `incident_date`, `preferred_outcome`, `confirm`.
- **Quotation detail extras** (line items, professional, appointment, other quotations) show when the context provides them; the model currently has only one fixed total.
- **Penalties**: no model/view yet; page shows an empty state until `penalties` is supplied.
- **Review form**: the `rating` select became 5 radio inputs with the same name and values; `comment` is unchanged.

## Hooks and behaviour
- `data-hook="…"` marks every block the backend is likely to fill (tables, forms, timelines, state banners).
- `customer.js` is opt-in through `data-cp-*` attributes (header comment lists them): mobile drawer, breadcrumb, confirm dialogs on Accept/Decline, once-only submit, character counters, file-size check, star rating, client tabs, copy/print, and the live service search (`services:search` JSON, params `q`, `category`, `region`).
- Django `messages` are rendered once by the shell. Do not include `payments/_messages.html` or `jobs/_messages.html` in customer pages.
- Breadpoints: 1280, 1024 (sidebar becomes a drawer), 768 (tables become stacked cards via `.is-stack` + `data-label`).
- Colours: navy text on the orange buttons and darker muted/grey text than the Figma values, to pass WCAG AA contrast.

## Checked
Rendered through a throwaway Django harness (not included) at 1440, 820 and 390 px: no console errors, no horizontal scroll; drawer, confirm dialog, rating, tabs and form validation exercised; admin and handyman job/complaint pages confirmed unchanged.

## Python wiring (customer_portal app)
- New app `customer_portal/` (urls, views, context processor for the unread badge); registered in `config/settings.py`, mounted in `config/urls.py`.
- `services/views.py` + `services/urls.py`: public `results/` page from approved `HandymanProfile`s.
- `dashboard/views.py`: `customer_dashboard` now supplies counts, recent requests, updates, next appointment.
- No models added, so no migration is needed for this app.
- Not stored yet: photo uploads on the new-request form, penalties, quotation line items; notification preferences live in the session only.
