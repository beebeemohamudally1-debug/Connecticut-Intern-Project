# Admin pages (frontend)

This file lists the admin pages built so far. **The admin frontend is still in progress:** some sections still require backend integration, including Manage Services, Manage Skills and Payments.

There are two kinds of pages:
- **Sample-data pages:** the two Registration Verification pages and the Manage Services pages. Registration Verification uses sample data from the views, while Manage Services uses demonstration data in the frontend. Administrative actions show demo messages until backend integration is completed.
- **Service Quotations**, **Material Quotations**, **Private Feedback**, **Reports**, **Complaints**, **Work Progress**, **Manage Users**, **Appointments** (saving still needed), **Service Requests** (forwarding still needed) and **Admin Profile** (see their own sections below): connected to the **payments**, **reviews**, **reports**, **complaints**, **jobs**, **accounts** and **bookings** apps, so they **already use the real backend**.

## Try it
```
python manage.py runserver
```
Open any URL below, for example http://127.0.0.1:8000/admin-portal/users/

## Demo data (for the pages connected to the backend)
Service Quotations, Material Quotations, Private Feedback, Reports, Complaints, Work Progress, Manage Users and Appointments show real data from the database, so they are empty until there is some. To fill your **local** database with demo data:
```
python manage.py seed_demo
```
It creates:
- demo users: one admin (`demo_admin`), customers and handymen, all with the password `demo12345`
- labour estimates to review, approved and waiting for the handyman
- labour quotations in every status (draft, sent, changes requested, accepted, paid, declined, cancelled)
- material purchase requests in every stage (admin review, rejected, with customer, changes requested, declined, approved, paid), with receipt images waiting for review and approved
- customer reviews (to assess, approved, rejected)
- complaints in every status (pending, in progress with private messages and a file, resolved with an outcome)
- jobs in every status, created on different days in the last two months and linked to the demo requests (so the report shows quotation amounts and payment states)
- arrival times, daily reports and photos for the open and completed jobs, with one delayed job and one flagged job
- inspection and service appointments in every status (pending, confirmed, completed, cancelled), with one pending appointment that clashes with a confirmed one
- service requests in every stage: not forwarded yet (with a sample chosen handyman), forwarded (no answer), rejected by the handyman (with a reason) and cancelled, next to the accepted ones
- phone numbers, two suspended accounts, and approved / pending / rejected skill and service changes for the handymen
- once the services app is there: 15 skills (3 inactive), handyman profiles with skills and areas, and skill requests to add, change and remove (`--reset` also deletes the demo skills, including the names used by the older version)

At the end it prints the links to open. To delete the demo data and create it again:
```
python manage.py seed_demo --reset
```
Notes:
- Log in on the login page (`/login`) as `demo_admin@example.com` with the password `demo12345` (or give your own account `role = 'admin'` and staff status) to open the pages.
- The ids change after `--reset`, so use the printed links or open the pages from the lists.
- Only for local testing. Every demo user starts with `demo_`, and nothing else in the database is changed. The command is in `payments/management/commands/seed_demo.py`.

## Pages
All URLs are in `accounts/admin_urls.py` (namespace `accounts_admin`, under `/admin-portal/`).

| URL | Name | Template | Sample data in the view |
|---|---|---|---|
| `users/handyman/verify/` | `handyman_verify` | `accounts/admin_handyman_verify.html` | `APPLICANT` |
| `users/handyman/documents/` | `handyman_documents` | `accounts/admin_handyman_verify.html` | `APPROVED_APPLICANT` |
| `notifications/` | `notifications` | `notifications/admin_notifications.html` | none: real notifications for the logged-in admin |
| `search/?q=` | `search` | `accounts/admin_search.html` | none: real users, jobs and service requests (navbar search) |

The **Admin Dashboard** (`dashboard/admin_dashboard.html`) is already connected to real data in `dashboard/services.py`.

## What each page needs
The full list of names is in the comment at the top of each template. The connected pages have more detail in their own sections below. Summary:

**Pages still on sample data**

- **Registration Verification** – `applicant`: id, name, email, submitted, status (`Pending`, `Approved` or `Rejected`), decided, notes, documents (title, file, action). Approve and Reject show only for `Pending`.

**Pages connected to the backend**

- **Notifications** – `notifications` (list of `Notification`: id, title, message, notification_type, is_read, created_at, newest first) and `unread_count`. Mark as read already posts to `notifications:mark_as_read` and `notifications:mark_all_as_read`. A notification with a `url` has its title as a link, so the admin can open the page it is about (it is marked as read on the way).
- **Logout** (profile menu in `base_admin.html`) posts to `accounts:logout`, which logs the admin out and opens the login page.
- **Manage Users** – `page.stats` (total, customers, handymen, pending) and `page.users` (name, initials, role, email, status, url). `url` is the user's Customer Details or Handyman Profile page.
- **Customer Details** – `customer`: name, initials, id, registered, email, phone, address, status (`Active` or `Suspended`), counts (submitted, completed, pending, cancelled), requests (id, title, status, state, url).
- **Handyman Profile** – `handyman`: name, initials, id, email, phone, areas, availability, status, verified, registered, completed, assigned, skills, services, reports_url.
- **Admin Profile** – `admin`: name, initials, email, role, status, from the logged-in user. Saving is not connected yet (no update view).
- **Labour estimates tab** – `estimates` (`LabourEstimate` list). The Review pop-up posts to the payments approve and revision views.
- **Quotations tab** – `quotations` (`Quotation` list, labour quotations).
- **Create Service Quotation** – `form`, `service_request`, `estimate`.
- **Revise Service Quotation** – `form`, `quotation`.
- **Service Quotation Details** – `quotation`, `other` (the material quotation of the same request) and `request_payment` (payment state of the whole request).
- **Material Quotations overview** – `purchase_requests` (each with `request`, `handyman`, `quotation`, and from the view `receipt_list`, `receipts_waiting`, `approved_total`, `difference`, `ready_to_schedule`).
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

- **Service Requests list** – `page.rows` (ref, customer, service, handyman, state, label, created, url), `page.stats` (all, review, forwarded, accepted) and `page.services`.
- **Service Request Details** – `page`: the request fields, the chosen `handyman` (`sample` when it is sample data), `response` (label, tone, details, answered on), `quotation_step` (accepted only) and the appointment / job links.
- **Appointments list** – `page.appointments` (ref, type, customer, handyman, date, slot, status, url) and the type counts.
- **Appointment Calendar** – `page.view` (`month`, `week` or `day`), the days with their `events`, and the previous / next links.
- **Appointment Details** – `page`: the appointment, customer, handyman, `checks` (payment rows and `ready`), `conflict` and `history`.
- **Schedule / Reschedule** – `page`: the request picker, `checks`, `handymen`, `busy` (confirmed slots per handyman, for the live availability check).

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
1. **Back to the handyman after a customer revision (FR-A-9 part A):** when the customer asks for changes, the admin should send them to the handyman, who updates the estimate; then the admin revises and re-issues the quotation. Now `LabourEstimate.request_revision` only works on a **submitted** estimate, so an approved one cannot be reopened. Details and the customer-response pop-up show a greyed-out **Ask Handyman to Update** button for this (marked `BACKEND`). Until then, **Revise is locked** for a quotation with a revision request, so the handyman step cannot be skipped: the Revise buttons, Save Draft and Send to Customer are greyed out, and `quotation_edit` refuses the POST (test `test_customer_revision_waits_for_the_handyman`). Unlock them once the handyman's updated estimate exists. This applies to material quotations too.
2. **A single-estimate page** (`estimates/<id>/`) for a full Review Labour Estimate page; for now the review is a pop-up on the list.
3. **Not stored yet:** line items (quantity, unit cost), the admin margin, estimate documents, a "response required by" date for revision requests, a note to customer, a decline reason and a "closed" status.
4. **Activity log** (including when a quotation was sent). The activity steps are built from the dates that exist, so "sent" has no date.
5. **Response prompts:** whether the admin has seen a customer's answer is kept in the browser (`localStorage`). Storing it would make it work per admin on any computer.
6. **Type filter** in `quotation_list`, so material quotations get their own list.
7. **Links and routes:** **Schedule Appointment** now opens the Appointments schedule page. Still missing: routes for `admin_dashboard`, `admin_record_payment` and `admin_issue_invoice`.
8. **Notifications** for estimates and customer answers (only complaints create notifications now), and `notify_admins` should include `role = 'admin'` users who are not staff.
9. **Payment for both quotations:** `ready_for_payment` and `payment_record` allow paying the labour quotation alone, and an appointment can be confirmed with only one paid quotation. Both should need the labour **and** material quotations accepted (and paid, for the appointment). The pages already follow this, but the backend still allows it through the URLs.

## Material Quotations (connected to the backend)
Built on the existing `payments` pages (same layout and pieces as Service Quotations). Needs an account with `role = 'admin'`.

**Flow (FR-A-9 part B)**
1. The handyman sends a material purchase request (materials and estimated cost).
2. The administrator approves it and sends the **material quotation** to the customer (no margin), or rejects it.
3. The customer approves it, rejects it or asks for changes.
4. The handyman buys the materials and uploads the receipts.
5. The administrator reviews the receipts.
6. The service quotation and the material quotation are paid (Record payment on each quotation's page, part C).
7. Once both are paid, **Schedule Appointment** opens the service schedule page.

There are only two quotations per request: the service (labour) quotation and the material quotation. All steps work now.

| Page | URL | Template |
|---|---|---|
| Purchase requests tab (Review and Receipts pop-ups) | `/payments/materials/` | `payments/admin_materials.html` |
| Quotations tab (the material quotations sent to customers) | `/payments/materials/quotations/` | `payments/material_quotation_list.html` (new) |
| Material Quotation Details | `/payments/quotations/<id>/` | `payments/quotation_admin_detail.html` (shared) |
| Revise Material Quotation | `/payments/quotations/<id>/edit/` | `payments/quotation_edit.html` (shared) |

- What the overview uses: `purchase_requests` (each with `request`, `handyman`, `quotation`, and from the view `receipt_list`, `receipts_waiting`, `approved_total`, `difference`).
- Stages: **Admin review** (submitted), **With customer** or **Changes requested** (quotation sent), **Receipts uploaded** (approved, receipts waiting), **Approved** or **Paid**, **Declined**, **Rejected**.
- **Review** pop-up: the materials and the estimated cost. **Approve and send to customer** posts `forward` with the total (it can be changed) to `payments:material_request_action`; **Reject** needs a reason.
- **Receipts** pop-up (view only): each `MaterialReceipt` with its image, amount and status, then the approved receipts, the material quotation and the difference. Receipts are approved or rejected in the payments section, not here. Then **Schedule Appointment** once both quotations are paid (payments themselves are the payments team's section).
- Details and revise pages: for a material quotation they say "Material Quotation", go back to Material Quotations and light up that sidebar item. Record payment works like the service quotation (once both quotations are accepted). When the customer approves, the prompt says the handyman can buy the materials, with **Review Receipts** (opens that request's receipts pop-up).
- The customer can ask for changes on the material quotation (`request_revision`). Like service quotations, the changes should go to the handyman first (greyed-out **Ask Handyman to Update**), then the administrator revises the quotation and sends it again.

**Changes outside the templates**
- `payments/views.py` and `payments/urls.py`: new read-only view `material_quotation_list` (`payments:material_quotation_list`) for the Quotations tab, like the Service Quotations tabs.
- `payments/views.py`: `admin_materials` also loads the receipts and works out `receipt_list`, `receipts_waiting`, `approved_total`, `difference` and `ready_to_schedule` (both quotations accepted and paid) for each purchase request. Nothing else changed.
- `config/urls.py`: uploaded files (`/media/`, for example the receipt images) are served while `DEBUG` is on.
- `templates/base_admin.html`: the sidebar **Material Quotations** link opens the overview.

**Still needed from the backend (payments)**
1. **Line items:** a purchase request has one text list and one estimated cost, so there is no quantity or unit cost per item.
2. **Attached documents** on a purchase request, and a **message to the customer** when the quotation is sent.
3. **Send a material request back to the handyman** when the customer asks for changes, so the handyman can update the materials and costs (like `LabourEstimate.resubmit`). Then the **Ask Handyman to Update** button can be enabled.
4. **Notify the handyman** when the customer approves the material quotation, so they know they can buy the materials (the payments app sends no notifications yet).
5. **Payment status page (payments team):** see "Payment status page" under Integration. Once it exists, add a **View Payment Status** button to the Receipts pop-up.

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

## Manage Users (connected to the backend)
| Page | URL | Template |
|---|---|---|
| Manage Users | `/admin-portal/users/` | `accounts/admin_users.html` |
| Customer Details | `/admin-portal/users/customer/<id>/` | `accounts/admin_customer_detail.html` |
| Handyman Profile | `/admin-portal/users/handyman/<id>/` | `accounts/admin_handyman_profile.html` |

- The views in `accounts/admin_views.py` read `accounts.User` (every customer and handyman, newest first). Only admins can open them.
- Status: `Suspended` (`is_suspended` or not `is_active`), else for a handyman `Pending` or `Rejected` from `HandymanProfile.status`, else `Active`. **Pending Approval** counts the handymen waiting for approval.
- Customer Details: the address is `user.address` (or the latest service request's address when it is empty). The counts and recent requests come from `bookings.ServiceRequest` (each request id opens Service Request Details); completed jobs from `jobs.Job`.
- Handyman Profile: skills, services and service areas come from `accounts.HandymanProfile` (areas fall back to `user.region`); **Verified** when the profile is approved. A handyman without a profile falls back to the approved `bookings.HandymanProfileRequest` changes. Completed and assigned jobs come from `jobs.Job`; **View Daily Work Report** opens the reports of the latest job.

**Still needed from the backend**
1. **Suspend, Reactivate and Delete** (`accounts/_user_modals.html`): no views yet, so the buttons only show a demo message.
2. **Registration documents and approve / reject:** the registration is still a stub, so no documents are stored and there is no view that approves or rejects a `HandymanProfile`. **Review registration** (pending handymen) and **View documents** still open the sample verification pages.
3. **Availability:** no field, so the profile shows "Not recorded".
4. **Job history:** no page for one handyman's jobs, so the button links to `#`.
5. **Approved skill and service requests:** approving a `HandymanProfileRequest` should also update `HandymanProfile.skills` / `.services`, so the profile shows the change.

## Appointments (connected to the backend, saving still needed)
Built from the low-fi and high-fi, with the same pieces as Service Quotations. Only admins can open them.

| Page | URL | Template |
|---|---|---|
| Appointments list | `/admin-portal/appointments/` | `bookings/admin_appointments.html` |
| Appointment Calendar (month, week, day) | `/admin-portal/appointments/calendar/` | `bookings/admin_appointment_calendar.html` |
| Appointment Details | `/admin-portal/appointments/<id>/` | `bookings/admin_appointment_detail.html` |
| Schedule Inspection / Service | `/admin-portal/appointments/schedule/inspection/` and `.../service/` (`?request=<id>`) | `bookings/admin_appointment_schedule.html` |
| Reschedule | `/admin-portal/appointments/<id>/reschedule/` | `bookings/admin_appointment_reschedule.html` |

- The views in `accounts/admin_appointments.py` (URLs in `accounts/admin_urls.py`) only **read** `bookings.Appointment`, `ServiceRequest` and the quotations to show the pages.
- **Nothing is saved yet**, because the bookings app has no views for it:
  - **Schedule** and **Reschedule** check the form and the booking conflict, then show "Not saved yet".
  - **Confirm** and **Cancel** pop-ups (`form[data-demo]`) close and show a demo message. Confirm also shows the "Appointment Confirmed" pop-up as a preview.
- Which requests can be scheduled: requests with an accepted handyman assignment. For a **service**, the labour quotation must be accepted, and the page blocks scheduling (the "Full Offline Payment Required" pop-up) until the labour and material quotations are accepted and paid.
- **Conflicts:** only **confirmed** appointments block a slot (the model's unique rule). The schedule and reschedule pages check the slot while you choose it and show the "Handyman Booking Conflict" pop-up. On Details, **Confirm** is greyed out while the slot clashes.
- **No double booking:** a request that already has a pending or confirmed appointment of that type is left out of the request picker. Opened directly (for example from Service Quotation Details), the page says "Already scheduled", links to that appointment and disables the form.
- **Date passed:** a Pending appointment whose date has passed shows "Date passed" in the list and a warning on Details (reschedule or cancel it).
- **Cancel** asks for a reason (required in the pop-up).
- Appointment ids are shown as `APT-1000 + id`. Slots are Morning (08:00 - 12:00) and Afternoon (13:00 - 17:00).
- **Schedule Appointment** on Service Quotation Details opens the service schedule page for that request.
- `templates/base_admin.html`: the sidebar **Appointments** link opens the list.

**Still needed from the backend (bookings)**
1. **Saving the actions** (the places are marked `BACKEND` in the view and templates):
   - **Schedule:** create a **Pending** `Appointment` (request, handyman, type, date, slot, notes), then open its details page.
   - **Confirm:** set it to Confirmed with `confirmed_by` and `confirmed_at`, refused if the handyman already has a confirmed appointment in that slot. Then set the Confirm form's `action`, remove `data-demo`, and open the "Appointment Confirmed" pop-up after it saves.
   - **Reschedule:** save the new date and slot, and put it back to Pending.
   - **Cancel:** set it to Cancelled and keep the reason (the pop-up sends `reason`; the model has no field for it yet). Then set the Cancel form's `action` and remove `data-demo`.
   - **Request status:** set the service request to **Booked** once its appointment is confirmed.
2. **Inspection fee:** not in the backend, so Details shows "Inspection fee: Not recorded in the system" and inspections can be scheduled without it.
3. **Proposal and customer answer:** there is no stored proposal, and the customer cannot accept or refuse it, so the Customer Confirmation card only shows that it is waiting.
4. **Handyman availability:** no working hours or days off, so availability only checks confirmed appointments.
5. **Exact times:** only Morning and Afternoon slots exist.
6. **Notifications** to the customer and handyman when an appointment is scheduled, confirmed, rescheduled or cancelled.
7. **Status history:** no log, so the history is built from `created_at`, `confirmed_at` and the current status.
8. **Payment status page (payments team):** the "Full Offline Payment Required" pop-up on Schedule Service has only Close for now. Once the payment status page exists, add a **View Payment Status** button to it (see Integration).
9. **Inspection before service (team decision):** a service can be scheduled without a completed inspection. In our flow the quotation comes after the inspection, so this is left open. Add a check if the team wants it strict.

## Service Requests (connected to the backend, forwarding still needed)
Built from the low-fi (FR-A-4) and the high-fi (screens 15 to 20), in the **bookings** app. Only admins can open them.

| Page | URL | Template |
|---|---|---|
| Manage Service Requests | `/bookings/admin/requests/` (`bookings:admin_requests`) | `bookings/admin_service_requests.html` |
| Service Request Details | `/bookings/admin/requests/<id>/` (`bookings:admin_request_detail`) | `bookings/admin_service_request_detail.html` |

- Views in `bookings/views.py`, URLs in `bookings/urls.py` (added to `config/urls.py` as `bookings/`). They only **read** `ServiceRequest` and `ServiceRequestAssignment` (`handyman_responses`).
- **Status** shown on the pages, worked out from the request status and the handyman's answer:
  - **Needs review:** not sent to a handyman yet (or the last one was withdrawn).
  - **Forwarded:** sent, no answer yet. **Accepted** / **Rejected:** the handyman's answer, with their note as "Details".
  - **Booked**, **Completed**, **Cancelled:** the request status.
- The **handyman** shown is the one the customer chose. Once the request is sent, it is the handyman it was sent to (real data). Before that the backend has no field for the customer's choice, so a **sample** handyman is shown with a "Sample" tag (`_chosen` in `bookings/views.py`).
- **List:** number cards (All, Needs review, Forwarded, Accepted), search, service / status / date filters, 5 rows per page.
- **Details:** Request Information, Handyman Response and Next Action:
  - Needs review: **Forward Request** pop-up: "Send SR-… to <handyman>, selected by the customer" (demo).
  - Accepted: the next step is the quotation (FR-A-9 part A), so the button follows where it stands: no button while waiting for the handyman's labour estimate, **Review Estimate** / **View Estimate** (opens that estimate's pop-up on the Labour estimates tab, `#est-<id>`), **Prepare Quotation** (estimate approved) or **View Quotation**.
  - Rejected: **Notify Customer** pop-up (demo).
  - Booked: **View Appointment** and **View Job**. Completed: **View Job**.
  - `?response=1` opens the "Handyman Accepted / Rejected" pop-up straight away (for links from notifications).
- `templates/base_admin.html`: the sidebar **Service Requests** link opens the list. The navbar search links service requests to their details page.

**Still needed from the backend (bookings)**
1. **Forward a request** to a handyman: a view that creates a `ServiceRequestAssignment` (status sent) and sets the request to "Sent to handymen". Then set the Forward form's `action` and remove `data-demo`.
2. **Handyman chosen by the customer:** `ServiceRequest` has no field for it (for example a `chosen_handyman` ForeignKey to the handyman). Until it exists, `_chosen` in `bookings/views.py` returns a **sample** handyman and the pages show a "Sample" tag. Once the field exists, return it there and remove the tag.
3. **Notify the customer** after a rejection (and the handyman when a request is forwarded): no notifications are sent by bookings yet. Then remove `data-demo` from the Notify form, and link the notifications to `?response=1`.
4. **Exact preferred time:** only a date and Morning / Afternoon exist, so the page shows "26 Nov 2026 · Afternoon".
5. **Attachments:** no photos or files on a request, so the page shows "No attachments".
6. **Services link:** the service is plain text (`service_category`), not linked to the Services app, so the Service filter lists the names found in the requests.

## Manage Services (Connected to the Backend)
### Backend Integration
- Connected all six Manage Services pages to the Django backend.
- Retrieved services, categories and handyman requests from the database.
- Implemented service creation, editing, viewing, deactivation and reactivation.
- Added optional service image uploads with file type and size validation.
- Implemented duplicate service validation.
- Displayed actual handyman assignments and pending request counts.
- Connected service request approval and rejection.
- Implemented Add, Modify and Remove service assignments upon approval.
- Recorded administrator notes, reviewer information and review dates.
- Prevented repeated decisions on previously reviewed requests.
- Implemented search, filters and client-side pagination with five records per page.
- Protected all service management endpoints with administrator access control.

### Testing
- Successfully tested service creation, editing, deactivation and reactivation.
- Successfully tested image uploads and duplicate validation.
- Successfully tested service request approval, modification, removal and rejection.
- Verified database updates after request approval.
- Tested search, filters and pagination.
- Removed temporary database test records.
- Ran the Django test suite. One previously existing error remains, with no new errors reported.

### Integration Notes
- Service creation and modification timestamps are not currently available in the Service model.
- Automatic cleanup of unused service image files is not currently implemented.
- Handyman service request submission depends on the Handyman module. The administrator-side review, approval and rejection functionalities have been implemented and tested using temporary database records.

## Manage Skills (connected to the backend, saving still needed)
Built from the low-fi and the high-fi (screens 08 to 14). Views in `accounts/admin_skills.py` (read only, admins only), URLs in `accounts/admin_urls.py`, templates in `templates/services/`. Category is the trade a skill belongs to (`Skill.category`, e.g. Plumbing).

| Page | URL |
|---|---|
| Manage Skills | `/admin-portal/skills/` |
| Skill Details (Deactivate / Reactivate pop-up) | `/admin-portal/skills/<id>/` |
| Add Skill / Edit Skill | `/admin-portal/skills/add/`, `/admin-portal/skills/<id>/edit/` |
| Handyman Skill Requests | `/admin-portal/skills/requests/` |
| Review Skill Request | `/admin-portal/skills/requests/<id>/` |

**Still needed from the backend (services)**
1. **Add / Edit a skill:** a view that saves the name, category and availability. Then set the form's `action` and remove `data-demo` (`services/admin_skill_form.html`).
2. **Deactivate / Reactivate:** a view that sets `Skill.is_active`. Then set the pop-up form's `action` and remove `data-demo` (`services/admin_skill_detail.html`).
3. **Approve / Reject a skill request:** a view that sets `status`, `admin_note`, `reviewed_at` and `reviewed_by`, and on approval adds, changes or removes the skill in the handyman's `HandymanProfile.skills`. Then set the form's `action` and remove `data-demo` (`services/admin_skill_request_detail.html`).
4. **Description and dates:** `Skill` has no description, created or updated date. The description is left out of the pages, and the list's **Updated** column shows "—" (marked `BACKEND`).
5. **Requested skill is text:** `HandymanProfileRequest.requested_value` is not linked to `Skill`, so the Review page links to the skill only when the name matches one in the catalogue.
6. **Keep a handyman's skills in one place:** Manage Skills and the Handyman Profile both read `HandymanProfile.skills`, so approving a request must update it (see item 3).

## Back links
`static/js/admin_back.js` (loaded by `base_admin.html`) makes the "← Back" link of every admin page go back to the admin page the admin came from, with its name ("Back to Skill Details", "Back to search results"). The pages and labels are the `PAGES` list at the top of the file: add a new admin page there.
- Where the admin came from is kept per page in `sessionStorage` (this tab only), so it stays after a refresh, a save that reloads the page, or the browser's Back button. Pressing a back link does not loop.
- Form pages (add, edit, schedule, reschedule, resolve) and the same page are never used as the place to go back to.
- Opened in a new tab, from a bookmark or from outside the admin pages, the link stays as written in the template.

## Navbar search (connected to the backend)
- The search box at the top of every admin page (`templates/base_admin.html`) opens `/admin-portal/search/?q=` (`accounts_admin:search`, view `search` in `accounts/admin_views.py`, template `accounts/admin_search.html`). Read only, admins only.
- It looks for every word of the search text in:
  - **Users** (customers and handymen): name, username, email, phone. Opens Customer Details or Handyman Profile.
  - **Jobs:** reference, service, address, customer or handyman name. Opens the job in Work Progress.
  - **Service requests:** reference, category, address, customer or contact name. Opens Service Request Details.
- Up to 6 results per group are shown; the rest is counted ("try a longer search").

## Integration (not done yet)
1. **Registration Verification:** once the backend has handyman verification, replace `APPLICANT` and `APPROVED_APPLICANT` with the real application, keeping the same names, and add the handyman id to the URLs.
2. **Buttons:** turn these into forms that post to real views:
   - Suspend, Reactivate and Delete (`accounts/_user_modals.html`)
   - Approve and Reject (`admin_handyman_verify.html`)
   - Save on the Admin Profile (remove `data-demo` once it saves)
   - Schedule, Reschedule, Confirm and Cancel on the Appointments pages (see Appointments)
   - Forward Request and Notify Customer on Service Request Details (see Service Requests)
3. **Lists:** search, filters and page buttons work in the browser on the rows sent. If you paginate on the server, send one page at a time and swap the page buttons for links. The search box on the page must then search on the server too.
4. **Payment status page (needed from the payments team):** a read-only page with its own URL that shows the payment status of a request: the service and material quotations, how much was paid, when and how, and what is still owed. The **Payments** link in the sidebar (`templates/base_admin.html`, now `/payments/admin-dashboard/`, which gives a 404) should open it too. It must be separate from **Record payment** (`payments:payment_record`), which is a form for entering a new payment, not for checking the status. Once it exists, add **View Payment Status** buttons that open it from:
   - the Receipts pop-up on Material Quotations (`payments/admin_materials.html`)
   - the "Full Offline Payment Required" pop-up on Schedule Service (`bookings/admin_appointment_schedule.html`)
5. **Manage Services:** connect the six completed frontend pages to the services backend, including service management and handyman service request approval / rejection. See the Manage Services section above.