# Service provider registration (S10, S10b, S11)

HTML, CSS and JS are finished. Backend: please do not change the templates; replace the stub views.
S02 to S06 are shared with the customer flow (see `FRONTEND_AUTH_README.md`). S18 (application status) already existed.

Try it: `/register` (pick Service Provider) or the home page option **I offer services**, then click through. Every state is at `/preview`.
Fake data: code `123456` is correct; username `taken`, `admin` or `handyconnect` is taken.

## Flow
`/register` (role) → email → confirm → verify → password → **S10 details** → **S10b documents** → **S11 submitted** → login → S18 status.
The home page options (**I need a service** / **I offer services**) POST the role to `accounts:register` and skip the chooser (S02).

## Files
| Path | What | New or changed |
|---|---|---|
| `templates/accounts/register_provider.html` | S10 details | new |
| `templates/accounts/register_provider_documents.html` | S10b documents | new |
| `templates/accounts/register_provider_done.html` | S11 application submitted | new |
| `templates/accounts/_pv_multiselect.html`, `_pv_upload.html`, `_pv_icons.html` | Partials: multiselect with chips, upload field, icons | new |
| `static/accounts/css/provider.css`, `static/accounts/js/provider.js` | Styles (classes start `pv-`) and behaviour | new |
| `templates/accounts/register_base.html` | Two optional blocks (`extra_css`, `extra_js`) and a "Part 1 of 2" label | changed (small) |
| `templates/accounts/_reg_steps.html` | Shows the part next to "Current step" | changed (one line) |
| `accounts/frontend_stubs_register.py` | Provider stub views, state tables, reference validators | changed |
| `accounts/auth_messages.py` | Provider copy and the service category list | changed (appended) |
| `accounts/urls.py` | Three routes | changed |
| `templates/accounts/home.html`, `static/accounts/css/home.css`, `static/accounts/js/home.js` | New home page whose two options start registration directly | replaced / new |

Note: the old home template linked `accounts/css/home.css` but the file was at `static/css/home.css`, so it did not load. The new one is at `static/accounts/css/home.css`; the old file can be deleted.

## Routes
| URL | Name | Template |
|---|---|---|
| `/register/provider` | `accounts:register_provider` | register_provider.html |
| `/register/provider/documents` | `accounts:register_provider_documents` | register_provider_documents.html |
| `/register/provider/done` | `accounts:register_provider_done` | register_provider_done.html |

After S06 the stub sends providers to `accounts:register_provider` (customers still go to `register_customer`).

## Context each template needs
All take `step`, `role` (`"provider"`) and `role_label` (`"Service Provider"`), as in the customer flow.
- **S10** (`step=4`, `part="Part 1 of 2"`): `email`, `values` {first_name, surname, additional_names, username, phone, address}, `regions` = `[(value, label)]` (nine), `categories` = `[(value, label)]` (eight), `selected_regions`, `selected_categories` (lists of values, to keep the ticks after an error), `errors` (same keys plus `regions`, `categories`).
  POST: the text fields, plus `regions` and `categories` as repeated fields (`request.POST.getlist("regions")`). Username is checked live on blur with the existing `accounts:username_check`.
- **S10b** (`step=4`, `part="Part 2 of 2"`): `name`, `email`, `errors` {id_photo, certificates, terms, privacy}, `terms_accepted`, `privacy_accepted`, `file_rules` {types, max_mb, type_error, size_error} (copy comes from `auth_messages`, so the page and the server say the same thing), optional `uploaded` (see below).
  POST is `multipart/form-data`: `id_photo` (one file), `certificates` (one or more files under the SAME field name: `request.FILES.getlist("certificates")`), `terms`, `privacy`.
- **S11** (`step=5`): `name`, `email`.

## Backend rules to enforce (the page only helps, the server decides)
1. **Nothing is created at S10.** Keep the S10 answers on the `RegistrationSession`. If S10b is opened without them, redirect to `accounts:register_expired`.
2. **Create the account at S10b in ONE transaction** (FR-SPR-10, 19): status `PENDING_APPROVAL`, role handyman, store consent (terms and privacy), store the ID photo and every certificate linked to that account. If any file fails, create nothing and re-render with `errors` (copy: `M.FILE_UPLOAD_FAILED`).
3. **Check every file**: JPEG or PNG, at most 5 MB each (FR-SPR-16). Check the real content, not only the extension or `content_type` (Pillow is already installed: `Image.open(f).verify()`). Re-render with `errors.id_photo` / `errors.certificates` using `M.FILE_TYPE_ERROR` / `M.FILE_SIZE_ERROR`; for several bad files join the messages with the file name first, as the stub does.
4. **At least one of each**: `M.DOC_ERRORS["id_photo"]` and `["certificates"]`. Both consents: `["terms"]`, `["privacy"]`.
5. **Documents are private**: do not serve them from public `MEDIA_URL`. Only an authorised administrator may open them (FR-SPR-18); the admin review page (S24) is the one place they appear.
6. After success go to `accounts:register_provider_done` (no auto-login). The provider logs in and lands on `accounts:provider_status`. Server limits: allow request bodies of at least 6 files x 5 MB.

## Files the server already holds (optional)
A browser cannot refill a file input, so after a validation error the user would have to pick the files again. If you keep uploads in temporary storage, pass `uploaded = {"id_photo": [f], "certificates": [f, ...]}` with `f = {token, name, type ("JPEG"/"PNG"), size ("2.1 MB"), url (to preview)}`. The page then shows them as normal rows and sends `keep_id_photo` / `keep_certificates` (the tokens) for every one the user did not remove. If you do not keep uploads, leave `uploaded` out; everything else works.

## States (names match `?state=`)
**S10**: `default`, `selected` (Figma "Default with selections"), `expanded` (Figma "Expanded multiselects"), `errors`, `taken`, `no_selection`.
**S10b**: `default` (Figma "Empty / default"), `uploaded` (Figma "Uploaded files"), `preview` (Figma "Larger preview"), `missing`, `bad_file`, `failed`, `terms`.
**S11**: one state.

## How the page works
- Multiselects: the real controls are the checkboxes in the menu, so a normal POST works; the chips, open/close and keyboard support (arrows, Esc) are `provider.js`. Without JavaScript the checkbox list is shown open.
- Uploads: the real control is a normal `<input type="file">`. The script checks type and size, shows a row with Preview / Replace / Remove, keeps the chosen files inside that input, and supports drag and drop. Without JavaScript the plain file input is shown.
- **Submit application** stays disabled until an ID photo, at least one certificate and both consents are present (Figma "Disabled submission").

## Decisions and differences from the Figma
- S10 description said "Continue to S10b to upload...". That is a design note, so the page says "Next, you will upload your ID card photo and your certificates."
- S10b subtitle "Provider details continuation · Jane Doe · email" became "Jane Doe · email", with the progress list showing "Part 2 of 2", and an info line "An administrator reviews these documents before your account is approved."
- Added (not in the design): section headings on S10, drag and drop, real image thumbnails and a real image in the preview, a "what happens next" list on S11, and a Status row on S11.
- Copy not in the design is marked NEW in `auth_messages.py` (error texts for regions, categories, documents, file type, file size, upload failure).
- Terms and Privacy links are `#` placeholders until those pages exist (same as the customer page).
- Disabled Submit uses the Figma grey, not the 50% opacity used elsewhere.
