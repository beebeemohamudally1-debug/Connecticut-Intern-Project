# Visitor landing page (frontend)

HTML, CSS and JS are finished. Backend: no template changes needed, the page renders with no context. It replaces the old S01 welcome page at `/` (route `accounts:home`).

## Files
| Path | What |
|---|---|
| `templates/accounts/home.html` | The page (replaced in place) |
| `templates/accounts/_home_join_pro.html` | New. "Join as a provider" one-button POST form, used 3 times |
| `static/accounts/css/home.css` | Styles, all classes `hm-*`, scoped under `.hm`. Self-contained (no auth.css). Brand colours are variables at the top |
| `static/accounts/js/home.js` | Nav shadow, mobile menu, inline search |
| `static/accounts/img/landing-hero.jpg`, `pro-*.jpg` | Photos exported from the Figma file (placeholders, swap for real ones) |

## Where it links
| Control | Goes to |
|---|---|
| Log in | `accounts:login` |
| Get started | `accounts:register` (role chooser) |
| Become a pro / Join as a professional / Join HandyConnect | POST `role=provider` to `accounts:register`, same as the role picker |
| Log out (signed-in users only) | POST `accounts:logout` |
| Find a service buttons | Scroll to and focus the search box |

## Search (the only backend hook)
Everything that searches uses the form's action, `services:search` (the existing route). Search button, "Popular" links, category cards, "View professional", "Meet all professionals" and the area chips.

- **With JS:** a `GET` with `Accept: application/json`, params `q`, `region`, `category` (empty ones are left out). Results show inline in `#results` with loading, empty and error (retry) states already built.
- **Without JS:** the same URL loads as a normal page.
- **Response expected:** `{"results": [{"id", "name", "category", "description"?, "url"?}]}`. The current `services.views.service_search` already returns this. `description` and `url` are optional.
- Each result links to `result.url`, or to the registration page if there is none.
- **Needs backend work:** `region` is sent but the route ignores it. Filter on `ServiceArea.name` when ready. Nothing in the frontend changes.
- If you want a full results page instead of inline results, return HTML when `Accept` is not JSON and delete the fetch part of `home.js`.

## Other `data-hook` markers in `home.html`
- `stat`: the four numbers in the blue band are copy from the design (12,000+, 850+, 5, 100%). Make them live if wanted. The design says 5 categories, the seed data has 8.
- `professional`: the three featured cards are samples. Loop over providers if wanted. Visitors have no profile page, so "View professional" opens search filtered by trade.
- `static-page`: 9 footer links (Help center, About, Contact, Trust & safety, Privacy, Terms, Accessibility, Professional resources) are `href="#"`. Those pages do not exist yet.
- Region `<select>`: hard-coded to the nine registration regions. Build from `ServiceArea` if you prefer.
- Area chips show the design's towns, but send the district they sit in (Quatre Bornes and Curepipe send Plaines Wilhems, Grand Baie sends Riviere du Rempart).

## Design notes
- Follows the Figma frame "Public · Home" section by section. Colours #132D49 and #EC763B are from that file (login pages use #142D48 and #F47939).
- Button text is navy on orange, not white as in the design: white on this orange is 2.9:1, navy passes AA (same call as the login pages). Small orange text and grey helper text are slightly darker than the design for the same reason.
- Breakpoints 1024 and 768. Under 1024 the nav becomes a menu button.
