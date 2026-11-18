# Admin pages (frontend)

This file lists the admin pages built so far. **The admin frontend is still in progress:** more sections (for example Services, Skills, Service Requests, Appointments, Material Quotations, Payments, Reports and Reviews) are still to be built.

There are two kinds of pages:
- **Sample-data pages** (the table under "Pages"): each view in `accounts/admin_views.py` sends **sample data** and renders one template. **Integration has not been done yet** for these: their buttons only show a demo message. Please do not change the templates when connecting real data; replace the sample data in the views, using the same names.
- **Service Quotations**, **Private Feedback**, **Reports**, **Complaints** and **Work Progress** (see their own sections below): connected to the **payments**, **reviews**, **reports**, **complaints** and **jobs** apps, so they **already use the real backend**.

## Try it
```
python manage.py runserver
```
Open any URL below, for example http://127.0.0.1:8000/admin-portal/users/

## Demo data (for the pages connected to the backend)
Service Quotations, Private Feedback, Reports, Complaints and Work Progress show real data from the database, so they are empty until there is some. To fill your **local** database with demo data:
```
python manage.py seed_demo
```
It creates:
- demo users: one admin (`demo_admin`), customers and handymen, all with the password `demo12345`
- labour estimates to review, approved and waiting for the handyman
- labour quotations in every status (draft, sent, changes requested, accepted, paid, declined, cancelled)
- material requests and quotations (labour accepted with no materials yet, both accepted and unpaid, both paid)
- customer reviews (to assess, approved, rejected)
- complaints in every status (pending, in progress with private messages and a file, resolved with an outcome)
- jobs in every status, created on different days in the last two months and linked to the demo requests (so the report shows quotation amounts and payment states)
- arrival times, daily reports and photos for the open and completed jobs, with one delayed job and one flagged job

At the end it prints the links to open. To delete the demo data and create it again:
```
python manage.py seed_demo --reset
```
Notes:
- Log in as `demo_admin` (or give your own account `role = 'admin'` and staff status) to open the pages.
- The ids change after `--reset`, so use the printed links or open the pages from the lists.
- Only for local testing. Every demo user starts with `demo_`, and nothing else in the database is changed. The command is in `payments/management/commands/seed_demo.py`.

## Pages
All URLs are in `accounts/admin_urls.py` (namespace `accounts_admin`, under `/admin-portal/`).

| URL | Name | Template | Sample data in the view |
|---|---|---|---|
| `users/` | `users` | `accounts/admin_users.html` | `USERS_PAGE` |
| `users/customer/` | `customer_detail` | `accounts/admin_customer_detail.html` | `CUSTOMER` |
| `users/customer/suspended/` | `suspended_customer` | `accounts/admin_customer_detail.html` | `SUSPENDED_CUSTOMER` |
| `users/handyman/` | `handyman_profile` | `accounts/admin_handyman_profile.html` | `HANDYMAN` |
| `users/handyman/suspended/` | `suspended_handyman` | `accounts/admin_handyman_profile.html` | `SUSPENDED_HANDYMAN` |
| `users/handyman/verify/` | `handyman_verify` | `accounts/admin_handyman_verify.html` | `APPLICANT` |
| `users/handyman/documents/` | `handyman_documents` | `accounts/admin_handyman_verify.html` | `APPROVED_APPLICANT` |
| `notifications/` | `notifications` | `notifications/admin_notifications.html` | none: real notifications for the logged-in admin |

The **Admin Dashboard** (`dashboard/admin_dashboard.html`) is already connected to real data in `dashboard/services.py`.

## What each page needs
The full list of names is in the comment at the top of each template. The connected pages have more detail in their own sections below. Summary:

**Pages still on sample data**

- **Manage Users** – `page.stats` (total, customers, handymen, pending) and `page.users` (name, initials, role, email, status, url). `url` is that user's details, profile or verification page.
- **Customer Details** – `customer`: name, initials, id, registered, email, phone, address, status (`Active` or `Suspended`), counts (submitted, completed, pending, cancelled), requests (id, title, status).
- **Handyman Profile** – `handyman`: name, initials, id, kind, email, phone, areas, availability, status, verified, registered, completed, assigned, skills, services.
- **Registration Verification** – `applicant`: id, name, email, submitted, status (`Pending`, `Approved` or `Rejected`), decided, notes, documents (title, file, action). Approve and Reject show only for `Pending`.

**Pages connected to the backend**

- **Notifications** – `notifications` (list of `Notification`: id, title, message, notification_type, is_read, created_at, newest first) and `unread_count`. Mark as read already posts to `notifications:mark_as_read` and `notifications:mark_all_as_read`.
- **Admin Profile** – `admin`: name, initials, email, role, status, from the logged-in user. Saving is not connected yet (no update view).
- **Labour estimates tab** – `estimates` (`LabourEstimate` list). The Review pop-up posts to the payments approve and revision views.
- **Quotations tab** – `quotations` (`Quotation` list, labour quotations).
- **Create Service Quotation** – `form`, `service_request`, `estimate`.
- **Revise Service Quotation** – `form`, `quotation`.
- **Service Quotation Details** – `quotation`, `other` (the material quotation of the same request) and `request_payment` (payment state of the whole request).
- **Private Feedback list** – `reviews`, `selected_status`, and `pending_count`, `approved_count`, `rejected_count`.
- **Feedback Details** – `review`. Approve and Reject post to `reviews:approve_review` and `reviews:reject_review`.
- **Job Summary Report** – `jobs` (each with `quotation_amount` and `payment_state`), the counts `total_jobs`, `assigned_jobs`, `in_progress_jobs`, `completed_jobs`, `cancelled_jobs`, and the filters `start_date`, `end_date`, `selected_status`, `status_choices`, `errors`.
- **Complaint Queue** – `page.stats` (total, pending, in_progress, resolved) and `page.complaints` (reference, subject, filed_by, role, job, created_at, status, url).
- **Case Overview / Resolve Case** – `page`: the complaint (reference, subject, description, job, filed_by, against, status), evidence, message counts, activity, the outcome once resolved, and the page links. Resolve also gets `page.checks` (customer_replied, handyman_replied, has_evidence).
- **Private chat** – the same `page`, plus who, person (name, initials, email), recipient_id, messages (author, from_admin, at, body) and next_url.
- **Work Progress Overview** – `page.services` and `page.jobs` (reference, service, customer, handyman, percent, due, status, status_label, url).
- **Job Progress Details** – `job`: reference, title, handyman, customer, started, due, service, request_ref, scheduled, status, percent, overdue, latest_note, last_report, is_flagged, flag_reason, timeline, reports_url, evidence_url.
- **Daily Work Reports** – `page`: reference, service, customer, job_url, handymen, reports (report_date, updated_at, handyman, details, percent, photos, url).
- **Work Evidence** – `page`: reference, title, back_url, back_label, report_date, updated_at, handyman, status, photos (caption, filename, url), notes, notes_title, is_flagged, flag_reason, flag_url, next_url.

Job `status` is `assigned`, `in_progress`, `completed` or `delayed` (`delayed` comes from `job.is_delayed`).

## Service Quotations (connected to the backend)
Built on the existing `payments` pages, so they use the real views, forms and models. Labour quotations only; material quotations are a separate section. Needs an account with `role = 'admin'`.

| Page | URL | Template |
|---|---|---|
| Labour estimates tab (Review pop-up) | `/payments/estimates/` | `payments/estimate_list.html` |
| Quotations tab | `/payments/quotations/` | `payments/quotation_list.html` |
| Create Service Quotation | `/payments/quotations/new/<request_id>/?estimate=<id>` | `payments/quotation_form.html` |
| Revise Service Quotation | `/payments/quotations/<id>/edit/` | `payments/quotation_edit.html` (new) |
| Service Quotation Details (customer-response prompts, link to the material quotation) | `/payments/quotations/<id>/` | `payments/quotation_admin_detail.html` |

CSS and JS are in `static/payments/`. The sidebar link **Service Quotations** points to `payments:estimate_list`.

**Changes in `payments/views.py`:**
- `quotation_edit` renders `quotation_edit.html` instead of the shared `form_page.html` (still used by the handyman forms), and **Send to Customer** on Revise saves and sends in one step.
- `quotation_detail_admin` also sends `other` (the material quotation of the same request, or the labour one for a material quotation) and `request_payment` (`request_payment_state`), because payment comes after **both** quotations are accepted. Record payment shows only then, and **Schedule Appointment** only when the whole request is paid.

**Demo data:** see "Demo data" at the top (`python manage.py seed_demo`).

**Still needed from the backend**
1. **Note to handyman** on Revise (shown but not connected): allow an estimate revision after approval when the customer asks for changes.
2. **A single-estimate page** (`estimates/<id>/`) for a full Review Labour Estimate page; for now the review is a pop-up on the list.
3. **Not stored yet:** line items (quantity, unit cost), the admin margin, estimate documents, a "response required by" date for revision requests, a note to customer, a decline reason and a "closed" status.
4. **Activity log** (including when a quotation was sent). The activity steps are built from the dates that exist, so "sent" has no date.
5. **Response prompts:** whether the admin has seen a customer's answer is kept in the browser (`localStorage`). Storing it would make it work per admin on any computer.
6. **Type filter** in `quotation_list`, so material quotations get their own list.
7. **Links and routes:** an appointment page for **Schedule Appointment**, and routes for `admin_dashboard`, `admin_record_payment` and `admin_issue_invoice`.
8. **Notifications** for estimates and customer answers (only complaints create notifications now), and `notify_admins` should include `role = 'admin'` users who are not staff.
9. **Login redirect:** `LOGIN_URL = 'login'` is missing in settings.
10. **Material process:** after the administrator approves a purchase request, the **customer approves the purchase** before the handyman buys, and the **material quotation is made from the actual costs on the receipts**. Now, forwarding a request creates a material quotation at the estimated cost straight away.
11. **Payment for both quotations:** `ready_for_payment` and `payment_record` allow paying the labour quotation alone, and an appointment can be confirmed with only one paid quotation. Both should need the labour **and** material quotations accepted (and paid, for the appointment). The pages already follow this, but the backend still allows it through the URLs.

## Private Feedback (connected to the backend)
Built on the existing `reviews` app: real views, URLs and the `Review` model. Needs an account with `role = 'admin'` **and staff status** (the reviews views check both).

| Page | URL | Template |
|---|---|---|
| Private Feedback list | `/reviews/admin/` | `reviews/admin_reviews.html` |
| Feedback Details (Approve / Reject) | `/reviews/admin/<id>/` | `reviews/review_detail.html` |

- The 4 review templates were moved from `reviews/templates/reviews/` to the main `templates/reviews/` (same names, so the views did not change). Only the two admin templates were restyled; `submit_review.html` and `my_reviews.html` (customer) are unchanged.
- CSS and JS: `static/reviews/css/admin_reviews.css`, `static/reviews/js/admin_reviews.js`.
- The sidebar link **Reviews** points to `reviews:admin_reviews`.
- List: number cards and status tabs use the view's `?status=` filter; search, the date filter and pages (5 rows) work in the browser on the rows sent.
- Details: Approve and Reject (pending only) ask for confirmation and post to `reviews:approve_review` / `reviews:reject_review`. After that the outcome, who assessed it and when are shown.

**Still needed from the backend**
1. No success message after Approve or Reject (the views do not add a Django message).
2. No admin note or reason with the assessment.

## Reports (connected to the backend)
Built on the existing `reports` app. Needs an account with `role = 'admin'` **and staff status**.

| Page | URL | Template |
|---|---|---|
| Job Summary Report | `/reports/job-summary/` | `reports/job_summary.html` |

- The template was moved from `reports/templates/reports/` to the main `templates/reports/` (same name, so the view did not change).
- CSS and JS: `static/reports/css/job_summary.css`, `static/reports/js/job_summary.js`.
- The sidebar link **Reports** points to `reports:job_summary`.
- Filters (a GET form): **Created from**, **Created to** and **Job status**. **Generate Report** reloads the page with the filters; **Clear** removes them. Wrong dates show the view's errors and no report.
- The 5 cards are the view's counts (total, assigned, in progress, completed, cancelled). The table shows job, customer, handyman, service, quotation amount, payment status, job status, created and completed dates, 5 rows per page.
- **Preview** shows the report as it will print (every row, no navigation); **Print** (or Ctrl+P) prints it on A4 landscape.

**Change in `reports/views.py`:** for FR-A-12.3, `job_summary_report` also adds to each job `quotation_amount` (total of the accepted labour and material quotations of its service request) and `payment_state` (`paid`, `partial`, `unpaid` or `none`). Nothing else in the view changed.

- The date filter uses the date the job was **created** (`created_at`), as agreed for FR-A-12.4.
- A job without a linked service request shows "No quotation".

## Complaints (connected to the backend)
The admin pages stay in the admin portal (the complaints app's own `complaint_list.html` and `complaint_detail.html` are shared with customers and handymen, so they were not changed). Their views in `accounts/admin_views.py` now read the real `Complaint`, `ComplaintMessage`, `ComplaintEvidence` and `ComplaintLog` data, and only admins can open them.

| Page | URL | Template |
|---|---|---|
| Complaint Queue | `/admin-portal/complaints/` | `complaints/admin_complaint_queue.html` |
| Case Overview (also a resolved case) | `/admin-portal/complaints/<id>/` | `complaints/admin_complaint_case.html` |
| Private chat with the customer / handyman | `/admin-portal/complaints/<id>/customer/` and `.../handyman/` | `complaints/admin_complaint_conversation.html` |
| Resolve Case | `/admin-portal/complaints/<id>/resolve/` | `complaints/admin_complaint_resolve.html` |

- **Start investigation** posts `status=in_progress`, and **Resolve** posts `status=resolved` and `outcome`, to `complaints:resolution`. **Send** in a chat posts `recipient` and `body` to `complaints:enquiry` (the first enquiry also moves a pending complaint to in progress).
- Each chat shows only the messages between the administrator and that person: enquiries sent to them and their own replies.
- The activity line comes from `ComplaintLog`; files open through `complaints:evidence_file`.

**Change in `complaints/views.py`:** `complaint_enquiry` and `complaint_resolution` go back to the page in the form's `next` field (only addresses on this site). Without `next` they go to `complaints:detail` as before, so the customer and handyman pages and the tests are unchanged.

**Still needed from the backend**
1. Admin notifications for new complaints link to `complaints:detail` (the shared page). They could link to `accounts_admin:complaint_case` instead (the notifications test checks the current link, so it needs updating too).
2. No assigned admin, category, priority or internal notes: the complaints app has no fields for them.

## Work Progress (connected to the backend)
The admin pages stay in the admin portal (the jobs app's own `job_list.html` and `job_detail.html` are shared with customers and handymen, so they were not changed). Their views in `accounts/admin_views.py` now read the real `Job`, `TimeLog`, `ProgressReport` and `WorkEvidence` data, and only admins can open them.

| Page | URL | Template |
|---|---|---|
| Work Progress Overview | `/admin-portal/work-progress/` | `jobs/admin_work_progress.html` |
| Job Progress Details | `/admin-portal/work-progress/<id>/` | `jobs/admin_job_progress.html` |
| Daily Work Reports | `/admin-portal/work-progress/<id>/reports/` | `jobs/admin_daily_reports.html` |
| Work Evidence (latest report) | `/admin-portal/work-progress/<id>/evidence/` | `jobs/admin_work_evidence.html` |
| Work Evidence (one report) | `/admin-portal/work-progress/<id>/evidence/<report id>/` | `jobs/admin_work_evidence.html` |

- The overview lists every job except cancelled ones. `status` is `assigned`, `in_progress`, `completed` or `delayed` (`delayed` comes from `job.is_delayed`, not a stored status).
- Progress is the latest report's `percent_complete` (0 with no report, 100 once the job is completed).
- The timeline is built from `created_at`, the first `TimeLog`, each `ProgressReport`, a missed due date, `completed_at` and the flag. Only the assignment and the latest 3 events are shown, so it fits one screen; every report is on Daily Work Reports.
- `WorkEvidence` belongs to the job, not to a report, so a report's photos are the ones uploaded on the report's day. Photos open through `jobs:evidence_file`.
- The notes card shows `completion_notes` once the job is completed, and the report's details before that.
- **Flag Submission** / **Remove Flag** posts `reason` to `jobs:flag`.

**Change in `jobs/views.py`:** `flag_job` goes back to the page in the form's `next` field (only addresses on this site). Without `next` it goes to `jobs:detail` as before, so the shared pages and the tests are unchanged.

**Still needed from the backend**
1. `WorkEvidence` has no link to a `ProgressReport`, so photos are matched to a report by upload day. A `report` field on `WorkEvidence` would make this exact.

## Admin Profile (partly connected)
| Page | URL | Template |
|---|---|---|
| Admin Profile | `/admin-portal/profile/` | `accounts/admin_profile.html` |

- The `profile` view in `accounts/admin_views.py` (admin only) shows the **logged-in** administrator: name (`get_full_name()`, or the username), initials, email, and status from `is_active`.

**Still needed from the backend**
1. **Saving:** there is no profile update view yet, so **Save changes** only updates the page and shows a demo message. When one exists, set the form's `action` to it, remove `data-demo` from the form, and read `full_name` and `email` from the POST.
2. **Change Password:** there is no change-password page yet, so the button links to `#`. Point it to that page when the authentication pages exist.

## Integration (not done yet)
1. **Access:** add `@role_required('admin')` (from `dashboard/permissions.py`) to the Manage Users views in `accounts/admin_views.py`. Right now anyone can open those pages (the other admin views already have it).
2. **Real data:** in each view, replace the sample dictionary with real data, keeping the same names.
3. **One user per page:** add the id to the URLs, for example `users/customer/<int:pk>/` (Complaints and Work Progress already do this). The suspended pages can then go, because the same template already handles both `Active` and `Suspended`.
4. **Buttons:** turn these into forms that post to real views:
   - Suspend, Reactivate and Delete (`accounts/_user_modals.html`)
   - Approve and Reject (`admin_handyman_verify.html`)
   - Save on the Admin Profile (remove `data-demo` once it saves)
5. **Lists:** search, filters and page buttons work in the browser on the rows sent. If you paginate on the server, send one page at a time and swap the page buttons for links. The search box on the page must then search on the server too.
6. **Navbar search bar:** the search box at the top of every admin page (in `templates/base_admin.html`) is not connected yet. To connect it:
   - Make a search view (for example `admin-portal/search/`) that reads the search text from `request.GET['q']` and shows the matching users, jobs and service requests.
   - In `base_admin.html`, set the form's `action` to that URL, add `name="q"` to the `<input>`, and remove `data-demo` from the `<form>`.