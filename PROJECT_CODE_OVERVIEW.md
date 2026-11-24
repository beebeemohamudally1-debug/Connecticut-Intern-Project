# HandyConnect Project Code Overview

## Scope and reading guide

This is a code-level overview of the Django project as it currently exists in the repository. It describes implemented models, routes, and workflows separately from frontend mockups and planned flows. It is not a claim that every page or business process is production-ready. No test suite was run while preparing this overview.

The most relevant files for bookings and requests are:

- `bookings/models.py` — service requests, handyman offers, appointments, and handyman profile change requests.
- `bookings/views.py` — customer request creation/history, handyman responses, admin forwarding, and customer appointment responses.
- `bookings/admin.py` — Django admin interfaces for those models.
- `payments/models.py` and `payments/views.py` — estimates, quotations, materials, and payment records tied to service requests.
- `jobs/models.py` and `jobs/views.py` — work performed after a request is selected and scheduled.
- `dashboard/services.py` — admin counts and activity summaries, including service requests and appointments.

## Overall structure

The project is a Django application with a custom user model and separate apps for the main business areas. `config/settings.py` registers the apps, configures Django authentication and templates, and currently uses a local SQLite database. `config/urls.py` mounts the app URL configurations.

### Apps and responsibilities

| App | Main responsibility | Current implementation level |
|---|---|---|
| `accounts` | Custom user, role field, registration/login pages, admin portal pages | User model and registration screens exist. The public login, password recovery, MFA, and provider status routes still use frontend stubs. Several admin portal pages render sample dictionaries. |
| `bookings` | Customer service requests, offers to handymen, appointments, handyman profile change requests | Models, forms, migrations, customer/handyman/admin routes, and appointment business services are present. |
| `payments` | Labour estimates, quotations, material requests/receipts, offline payment records | Model actions and role-guarded routes exist for admin, handyman, and customer payment flows. They are attached to `ServiceRequest`. |
| `jobs` | Assigned work, time logs, progress, evidence, completion, admin flagging | Functional role-protected list/detail and POST action views exist. Jobs may optionally reference a service request. |
| `dashboard` | Admin statistics and dashboard plus handyman/customer dashboard routes | Admin dashboard uses aggregated database data. Many handyman pages render templates without model-backed context; customer dashboard template is referenced but absent from the repository. |
| `complaints` | Complaints between parties to a job, private enquiries/replies, resolution and evidence | Functional views, forms, models, permissions, and signals exist. |
| `notifications` | Admin notification records and JSON endpoints | Database-backed creation and admin-only notification JSON endpoints exist. Service request creation can generate admin notifications. |
| `reviews` | Customer reviews of completed jobs and admin assessment | Functional customer and admin views and review model exist. |
| `reports` | Admin job summary report | Functional admin-only report view, filtering job records and summarizing accepted quotations and payments. |

There is also `accounts/admin_views.py`, which holds custom admin portal pages. Some functions in it are functional, while a number of user, work-progress, and complaint screens still render hard-coded demo data. The `ADMIN_FRONTEND_README.md` documents known integration work for those screens.

## Booking and service request domain

The word “booking” currently refers to several related records rather than one complete customer-facing workflow.

### 1. `ServiceRequest`

Defined in `bookings/models.py`, a service request is the customer's description of work they need. It stores:

- Customer account.
- Service category and problem description.
- Service address and contact details.
- Optional preferred date and preferred time slot (`morning` or `afternoon`).
- Status and timestamps.
- A generated public reference in the form `SR-1000 + database id`.

The declared status values are `requested` (legacy default), `submitted`, `reviewing`, `assigned`, `booked`, `cancelled`, and `completed`. The model also stores the customer's chosen handyman. Its `clean()` checks the customer and handyman roles, and `save()` generates a reference after the first insert. New requests are created as `submitted` through a customer-only form; the owner comes from the signed-in account.

Customer routes provide request submission, history, and detail pages. Requests are scoped to their owner. After a handyman declines, the customer may choose another active handyman; a previously contacted handyman cannot be selected again for that request.

### 2. `ServiceRequestAssignment`

This model represents offering one service request to a handyman and recording that handyman's response. It connects a request to a handyman and stores:

- Status: `sent`, `accepted`, `rejected`, or `withdrawn`.
- Who sent the offer, when it was sent, when the handyman responded, and an optional response note.
- A database uniqueness constraint prevents a second offer record for the same request/handyman pair.

Admins can forward a request to the selected handyman, and handymen can accept or decline their own pending offers. These transitions are transactional, record response time and notes, update request state, and create notifications. Payment views require an accepted assignment before a handyman can submit an estimate or material request.

### 3. `Appointment`

An appointment connects a service request to a handyman and stores appointment type (`inspection` or `service`), date, time slot, status (`pending`, `confirmed`, `cancelled`, `completed`), notes, confirmation actor, and timestamps.

The model's `clean()` checks that:

- The selected person has the handyman role.
- The handyman has an accepted `ServiceRequestAssignment` for the request.
- A confirmed proposal has been accepted by the customer; service appointments also require the labour quotation and any issued material quotation to be accepted and paid.
- A handyman does not have another confirmed appointment in the same date/time slot.

The last rule is also enforced by a conditional database uniqueness constraint for confirmed appointments, which is the strongest of these appointment checks. The other checks live in `clean()`; the model does not override `save()` to always call `full_clean()`, so code that inserts/updates appointments directly must explicitly validate them. Django admin forms generally validate model fields, but direct ORM calls are not guaranteed to run `clean()`.

There are two notable workflow concerns:

- The payment check in `Appointment.clean()` accepts the existence of *any one* accepted quotation with a payment. It does not itself require both a labour and a material quotation to be accepted and paid. `payments/models.py` has `request_payment_state()` and `request_fully_paid()` helpers that can represent aggregate payment status, but the appointment check does not use them.
- Admin routes create pending proposals, reschedule them back to pending, confirm after customer acceptance, and cancel with a required reason. Customers can accept or decline a proposal. Notifications are stored for the customer and handyman, and appointment events provide a persisted history.
- Confirming a service appointment sets the service request to `booked` and creates or updates its job. Completing the job marks the request and confirmed service appointment complete.

### 4. `HandymanProfileRequest`

This is not a customer job request. It is a handyman's request to add, modify, or remove a service or skill on their profile. It stores the current/requested value, reason, pending/approved/rejected status, admin note, submission/review timestamps, and reviewer. The model validates that a handyman is selected and that required values are present for each action. Its current interface is through Django admin; no self-service handyman route was found.

## Request-to-work lifecycle: data exists, orchestration is incomplete

The models and neighboring apps imply the following intended path:

```text
Customer creates ServiceRequest
        ↓
Admin reviews request and sends it to one or more handymen
        ↓
Handyman accepts an assignment
        ↓
Handyman submits labour estimate and may submit material request
        ↓
Admin reviews estimate/material request and creates/sends quotations
        ↓
Customer accepts quotations; admin records offline payment(s)
        ↓
Admin schedules/ confirms Appointment
        ↓
Job is created and handyman performs work
        ↓
Completion → possible complaint/review/report
```

The core sequence is now connected across the request, payment, appointment, and job apps:

- Customers submit service requests and choose an active handyman; admins forward the request; the handyman responds; estimate/quotation/payment flows run against that request; admins propose appointment slots; customers respond; admins confirm; and job completion closes the appointment and request.
- Service appointments require an accepted and paid labour quotation, plus any issued material quotation to be accepted and paid. Database constraints protect confirmed handyman slots and prevent multiple active appointments of the same type for one request.
- Initial requests use `submitted`; forwarding/acceptance uses `assigned`; rejection returns the request to `reviewing`; confirmation sets `booked`; job completion sets `completed`.

## Payments and their relationship to requests

`payments` provides the richest downstream connection to booking records:

- `LabourEstimate` belongs to a `ServiceRequest` and a handyman. An admin can approve, reject, or request a revision; a handyman can resubmit after a revision request.
- `MaterialPurchaseRequest` belongs to a request and a handyman. It can be forwarded by an admin as a material quotation or rejected. Material receipts can be uploaded and reviewed.
- `Quotation` belongs to a request and has a type (`labour` or `material`), fixed total in MUR, work description, status, revision count, and customer response fields. It supports sent/accepted/declined/revision-requested states.
- `Payment` is a one-to-one full offline payment record for a quotation, with amount, date, cash/bank transfer method, optional reference, and recording administrator. Model validation requires the amount to equal the full quotation total.

Role-guarded routes are defined in `payments/urls.py` for admin estimate/quotation/payment management, handyman estimates/material purchases/receipts, and customer quotations/payment history. These flows rely on an accepted service-request assignment for some handyman actions.

The admin quotation detail template has a “Schedule Appointment” button with `href="#"` and an explicit note that scheduling has no URL yet. The payment/readiness flow also needs careful tightening so the backend consistently enforces the intended condition that all required quotation types are accepted and paid before scheduling.

## Jobs, complaints, reviews, and reports

### Jobs

`Job` is the work-execution record. It has customer and handyman, service name/description/address, status (`assigned`, `in_progress`, `completed`, `cancelled`), schedule/due date, completion notes, payout stage, optional `service_request`, and admin flag fields. Its related records are:

- `TimeLog` for handyman clock-in/clock-out and duration.
- `ProgressReport` for daily notes and percentage complete, unique per job/day.
- `WorkEvidence` for uploaded JPG/PNG photos.

`jobs/views.py` implements role-scoped list/detail, handyman clock-in/out, daily reports, evidence upload, completion and payout state changes, admin flagging, and permission-checked evidence downloads. Customers and handymen see their own jobs; admins can see all jobs. This is a working job execution subsystem, but it is downstream of a booking process that is not yet connected.

### Complaints

Complaints attach to jobs, not directly to service requests or appointments. A complaint has submitter, other party, subject/description, status, outcome, resolver and timestamps. `ComplaintMessage` represents admin enquiries and party replies; `ComplaintEvidence` stores evidence; `ComplaintLog` records status changes. Views restrict access to the parties and admin, provide file access checks, and prevent party users from seeing each other's private responses. Signals can notify admins when a complaint is submitted.

### Reviews

A review is a one-to-one record on a completed job. It is restricted to the customer who owns the job and supports rating, comment, and admin approval/rejection. The model runs `full_clean()` from `save()` to enforce job completion, ownership, and customer role.

### Reports

The job summary report is admin-only and filters jobs by created date and job status. It totals job statuses and derives accepted quotation amounts/payment state from the job's related service request. Jobs without a service request do not have quotation data to summarize.

## Dashboards, notifications, and frontend status

- `dashboard/services.py` calculates admin counts for users, jobs, service requests, appointments, payment and pending tasks, and combines recent activity. `dashboard/views.py` renders the admin dashboard with these values.
- The admin dashboard service still counts both legacy/current request states such as `requested` and `submitted` for backward compatibility.
- `notifications` stores recipient, notification type/title/message/URL, read status, and creation time. New service requests notify active staff admins; request/appointment actions notify relevant customers and handymen. Existing admin notification routes remain admin-only, and `/notifications/mine/` endpoints return only the signed-in user's own notifications.
- Customer request/appointment pages and a handyman request inbox are available. Other dashboard pages still contain placeholders, and the custom customer dashboard template remains missing although its view references it.
- Login and registration screens exist visually, but `accounts/urls.py` still wires login/recovery/MFA/status routes to stub functions. In particular, the login stub redirects every POST to the customer dashboard without authenticating; it is not a production login flow.
- `accounts/admin_views.py` includes hard-coded sample data for several admin pages; its README lists remaining access-control and data integration work.

## Data, migrations, and development setup

- The configured database is SQLite at the project root (`db.sqlite3`).
- The custom user model is `accounts.User`, extending Django's `AbstractUser` with `role` (`customer`, `handyman`, `admin`) and phone.
- Booking migrations create the initial request table, then assignments, appointments, handyman profile requests, and the expanded service-request fields/status/reference.
- The current settings have `DEBUG = True`, an in-code development secret, and no `ALLOWED_HOSTS` entries. These are local-development settings, not deployment-ready settings.
- Upload models use `MEDIA_ROOT` and some views serve files after permission checks. Deployment must configure private/media storage appropriately.

## Remaining booking decisions and limits

- The project does not specify an inspection-fee amount or how such a fee is issued/paid. Inspection scheduling remains possible without an inspection-fee record; the fee policy needs a product decision before it can be enforced.
- Time slots remain Morning (08:00–12:00) and Afternoon (13:00–17:00). There is no working-hours/day-off model for handyman availability.
- Customer request attachments are not stored yet. The request form currently collects text/contact information and a preferred date/slot.
- Notifications are persisted in-app and available through authenticated JSON endpoints; email/SMS delivery is not configured.
- Login routes still use the separate authentication frontend stubs described in `FRONTEND_AUTH_README.md`; the booking routes require authenticated sessions.
- Migration `0006` adds the chosen handyman, customer response, cancellation reason, and appointment event model; `0007` adds the active-appointment uniqueness constraint. Apply the migrations with `python manage.py migrate` before using these fields.
- `bookings/tests.py` remains a placeholder. No tests were run while implementing these workflows.
