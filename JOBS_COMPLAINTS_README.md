# Jobs and Complaints (back-end module 4)

## Set up
1. Unzip over the repo root (new folders `jobs/`, `complaints/`, `templates/jobs/`, `templates/complaints/`, `static/css/jobs.css`).
2. Three shared files were edited, check them in your diff: `config/settings.py` (apps added), `config/urls.py` (two routes), `templates/base_admin.html` (Jobs link, Complaints link now points to the real page).
3. Create the tables, then run the tests:
   ```
   python manage.py makemigrations jobs complaints
   python manage.py migrate
   python manage.py test jobs complaints
   ```
4. Create users with `role` set to `admin`, `customer` or `handyman`. A superuser is treated as admin even though `createsuperuser` leaves `role` as `customer`.

## URLs
| Path | Who | What |
|---|---|---|
| `/jobs/` | all | Job list (admin: filters by handyman, status, delayed, flagged) |
| `/jobs/<id>/` | all | Job detail: reports, photos, time on site |
| `/jobs/<id>/clock-in/`, `clock-out/`, `report/`, `evidence/`, `complete/`, `payout/waiting|finished/` | handyman | Work actions (POST) |
| `/jobs/<id>/flag/` | admin | Flag or unflag a submission (POST) |
| `/complaints/` | all | Complaint list (admin: filter by status, submitter) |
| `/complaints/new/` | customer, handyman | File a complaint about one of your jobs |
| `/complaints/<id>/` | parties, admin | Detail, history, messages |
| `/complaints/<id>/reply/` | parties | Respond to the administrator, attach evidence |
| `/complaints/<id>/enquiry/`, `resolution/` | admin | Ask a party for information; set status and outcome |

## Rules built in
- A user only sees their own jobs and complaints (other people's get a 404). Admins see everything.
- A complaint is tied to a job the filer is part of. The other party is filled in automatically.
- Each party sees only their own replies and the enquiries sent to them, never the other side's explanation. Admins see everything.
- Resolving needs an outcome. A resolved complaint is locked. Complaint records cannot be edited or deleted in Django admin.
- Photos: JPG or PNG up to 5 MB (complaint evidence also allows PDF). Files are served through a permission check, not a public URL.

## Hooks for teammates
- **Notifications**: connect receivers to the signals in `jobs/signals.py` (`job_completed`) and `complaints/signals.py` (`complaint_submitted`, `complaint_enquiry_sent`, `complaint_response_received`, `complaint_status_changed`).
- **Bookings / quotations**: `Job.request_ref` is a plain text field for now. Once `bookings.ServiceRequest` exists, replace it with a ForeignKey. Jobs should be created after payment is cleared and the appointment is set. Until then, create them in Django admin.
- **Payments**: the handyman's "waiting for payout" and "finished work" steps are here. Uploading proof of payment (FR-H-6.3) belongs to the payments app.
- `LOGIN_URL` is not set yet. Set it once the accounts login page exists.
