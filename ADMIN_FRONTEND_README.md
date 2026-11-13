# Admin pages (frontend)

The HTML, CSS and JS for these admin pages are finished. Each view in `accounts/admin_views.py` sends **sample data** and renders one template.
Backend: please do not change the templates; replace the sample data in the views with real data, using the same names.

## Try it
```
python manage.py runserver
```
Open any URL below, for example http://127.0.0.1:8000/admin-portal/users/

## Pages
All URLs are in `accounts/admin_urls.py` (namespace `accounts_admin`, under `/admin-portal/`).

| URL | Name | Template | Sample data in the view |
|---|---|---|---|
| `profile/` | `profile` | `accounts/admin_profile.html` | `ADMIN_PROFILE` |
| `users/` | `users` | `accounts/admin_users.html` | `USERS_PAGE` |
| `users/customer/` | `customer_detail` | `accounts/admin_customer_detail.html` | `CUSTOMER` |
| `users/customer/suspended/` | `suspended_customer` | `accounts/admin_customer_detail.html` | `SUSPENDED_CUSTOMER` |
| `users/handyman/` | `handyman_profile` | `accounts/admin_handyman_profile.html` | `HANDYMAN` |
| `users/handyman/suspended/` | `suspended_handyman` | `accounts/admin_handyman_profile.html` | `SUSPENDED_HANDYMAN` |
| `users/handyman/verify/` | `handyman_verify` | `accounts/admin_handyman_verify.html` | `APPLICANT` |
| `users/handyman/documents/` | `handyman_documents` | `accounts/admin_handyman_verify.html` | `APPROVED_APPLICANT` |
| `notifications/` | `notifications` | `notifications/admin_notifications.html` | `NOTIFICATIONS` |
| `work-progress/` | `work_progress` | `jobs/admin_work_progress.html` | `WORK_PROGRESS` |
| `work-progress/job/` | `work_progress_job` | `jobs/admin_job_progress.html` | `JOB_PROGRESS` |
| `work-progress/reports/` | `work_progress_reports` | `jobs/admin_daily_reports.html` | `DAILY_REPORTS` |
| `work-progress/evidence/` | `work_progress_evidence` | `jobs/admin_work_evidence.html` | `WORK_EVIDENCE` |
| `complaints/` | `complaints` | `complaints/admin_complaint_queue.html` | `COMPLAINT_QUEUE` |
| `complaints/case/` | `complaint_case` | `complaints/admin_complaint_case.html` | `CASE_OPEN` |
| `complaints/case/resolved/` | `complaint_case_resolved` | `complaints/admin_complaint_case.html` | `CASE_RESOLVED` |
| `complaints/case/customer/` | `complaint_customer` | `complaints/admin_complaint_conversation.html` | `CONVERSATIONS['customer']` |
| `complaints/case/handyman/` | `complaint_handyman` | `complaints/admin_complaint_conversation.html` | `CONVERSATIONS['handyman']` |
| `complaints/case/resolve/` | `complaint_resolve` | `complaints/admin_complaint_resolve.html` | `CASE_RESOLVE` |

The **Admin Dashboard** (`dashboard/admin_dashboard.html`) is already connected to real data in `dashboard/services.py`.

## What each page needs
The full list of names is in the comment at the top of each template. Summary:

- **Admin Profile** – `admin`: name, initials, email, role, status (the logged-in administrator).
- **Manage Users** – `page.stats` (total, customers, handymen, pending) and `page.users` (name, initials, role, email, status, url). `url` is that user's details, profile or verification page.
- **Customer Details** – `customer`: name, initials, id, registered, email, phone, address, status (`Active` or `Suspended`), counts (submitted, completed, pending, cancelled), requests (id, title, status).
- **Handyman Profile** – `handyman`: name, initials, id, kind, email, phone, areas, availability, status, verified, registered, completed, assigned, skills, services.
- **Registration Verification** – `applicant`: id, name, email, submitted, status (`Pending`, `Approved` or `Rejected`), decided, notes, documents (title, file, action). Approve and Reject show only for `Pending`.
- **Notifications** – `notifications` (list of `Notification`: id, title, message, notification_type, is_read, created_at, newest first) and `unread_count`. Mark as read already posts to `notifications:mark_as_read` and `notifications:mark_all_as_read`.
- **Work Progress Overview** – `page.services` and `page.jobs` (reference, service, customer, handyman, percent, due, status, status_label, url).
- **Job Progress Details** – `job`: see the template comment. `request_ref` comes from `job.service_request.reference`.
- **Daily Work Reports** – `page`: reference, service, customer, job_url, handymen, reports (one per `ProgressReport`).
- **Work Evidence** – `page`: reference, title, report details, photos (one per `WorkEvidence`), notes, is_flagged, flag_reason, flag_url. The Flag form posts `reason` to `jobs:flag`.
- **Complaint Queue** – `page.stats` (total, pending, in_progress, resolved) and `page.complaints` (reference, subject, filed_by, role, role_label, job, created_at, status, status_label, url). `url` is that complaint's case page.
- **Case Overview** (also the resolved view) – `page`: reference, subject, description, job, filed_by, against, created_at, status, status_label, is_resolved, evidence (name, size, url), customer_msgs, handyman_msgs, activity (from `ComplaintLog`), and when resolved: outcome, resolved_by, resolved_at. The links are `queue_url`, `customer_url`, `handyman_url`, `resolve_url`. "Start investigation" posts `status=in_progress` to `complaints:resolution` (`status_url`).
- **Private chats** (customer and handyman use one template) – `page`: the complaint fields above, `who` (`Customer` or `Handyman`), `person` (name, first_name, initials, email), `recipient_id`, `messages` (author, role, at, body, from_admin) for **that person only**, and `case_url`, `other_url`, `other_label`. Send posts `recipient` and `body` to `complaints:enquiry` (`enquiry_url`). The reply box is hidden when `is_resolved`.
- **Resolve Case** – `page`: reference, subject, filed_by, against, `case_url`, `resolution_url`, `checks` (customer_replied, handyman_replied, has_evidence). The form posts `status=resolved` and `outcome` (required) to `complaints:resolution`.

`status` for jobs is `assigned`, `in_progress`, `completed` or `delayed` (`delayed` comes from `job.is_delayed`).

`status` for complaints is `pending`, `in_progress` or `resolved`. The complaint pages have no assigned admin, category, priority, internal notes or payment amount, because the complaints app has no data for them.

## Backend: how to take over
1. **Access:** add `@role_required('admin')` (from `dashboard/permissions.py`) to every view in `accounts/admin_views.py`. Right now anyone can open these pages.
2. **Real data:** in each view, replace the sample dictionary with real data, keeping the same names.
3. **One user, job or complaint per page:** add the id to the URLs, for example `users/customer/<int:pk>/`, `work-progress/<int:pk>/` and `complaints/<int:pk>/` (with `customer/`, `handyman/` and `resolve/` after it). The suspended pages can then go, because the same template already handles both `Active` and `Suspended`.
4. **Buttons:** turn these into forms that post to real views:
   - Suspend, Reactivate and Delete (`accounts/_user_modals.html`)
   - Approve and Reject (`admin_handyman_verify.html`)
   - Save on the Admin Profile (remove `data-demo` once it saves)
5. **Lists:** search, filters and page buttons work in the browser on the rows sent. If you paginate on the server, send one page at a time and swap the page buttons for links. The search box on the page must then search on the server too.
6. **Navbar search bar:** the search box at the top of every admin page (in `templates/base_admin.html`) is not connected yet. To connect it:
   - Make a search view (for example `admin-portal/search/`) that reads the search text from `request.GET['q']` and shows the matching users, jobs and service requests.
   - In `base_admin.html`, set the form's `action` to that URL, add `name="q"` to the `<input>`, and remove `data-demo` from the `<form>`.