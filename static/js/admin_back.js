/* Admin pages: smart back links.
   A back link (a link in the page whose text starts with "←") normally goes to its section's
   list. When the admin came from another admin page, it goes back there instead, with a label
   that names that page ("Back to Skill Details", "Back to search results"...).

   - Where the admin came from is kept per page in sessionStorage (this tab only), so the link
     stays the same after a refresh, a save that reloads the page, or the browser's Back button.
   - Pressing a back link keeps that page's own "came from", so going back twice does not loop.
   - Form pages (add, edit, schedule, reschedule, resolve) are never used as the place to go back
     to, and neither is the same page. Opened from outside the admin pages, in a new tab or from a
     bookmark, the link stays as written in the template. */
(function () {
  var main = document.getElementById('main');
  if (!main) return;
  var links = Array.prototype.filter.call(main.querySelectorAll('a[href]'), function (a) {
    return a.textContent.trim().charAt(0) === '←';
  });
  if (!links.length) return;

  /* Admin pages that can be gone back to, and their labels (first match wins) */
  var PAGES = [
    [/^\/dashboard\/admin\/$/, 'Dashboard'],
    [/^\/admin-portal\/search\/$/, 'search results'],
    [/^\/admin-portal\/notifications\/$/, 'Notifications'],
    [/^\/admin-portal\/profile\/$/, 'My Profile'],
    [/^\/admin-portal\/users\/$/, 'Manage Users'],
    [/^\/admin-portal\/users\/customer\/\d+\/$/, 'Customer Details'],
    [/^\/admin-portal\/users\/handyman\/\d+\/$/, 'Handyman Profile'],
    [/^\/admin-portal\/users\/handyman\/(verify|documents)\/$/, 'Registration Verification'],
    [/^\/admin-portal\/skills\/$/, 'Manage Skills'],
    [/^\/admin-portal\/skills\/\d+\/$/, 'Skill Details'],
    [/^\/admin-portal\/skills\/requests\/$/, 'Skill Requests'],
    [/^\/admin-portal\/skills\/requests\/\d+\/$/, 'the skill request'],
    [/^\/bookings\/admin\/requests\/$/, 'Service Requests'],
    [/^\/bookings\/admin\/requests\/\d+\/$/, 'Service Request Details'],
    [/^\/payments\/estimates\/$/, 'Labour Estimates'],
    [/^\/payments\/quotations\/$/, 'Service Quotations'],
    [/^\/payments\/quotations\/\d+\/$/, 'Quotation Details'],
    [/^\/payments\/materials\/(quotations\/)?$/, 'Material Quotations'],
    [/^\/admin-portal\/payments\/\d+\/$/, 'Payment Status'],
    [/^\/payments\/invoices\/$/, 'Invoices'],
    [/^\/admin-portal\/appointments\/$/, 'Appointments'],
    [/^\/admin-portal\/appointments\/calendar\/$/, 'Calendar'],
    [/^\/admin-portal\/appointments\/\d+\/$/, 'Appointment Details'],
    [/^\/admin-portal\/work-progress\/$/, 'Work Progress'],
    [/^\/admin-portal\/work-progress\/\d+\/$/, 'Job Progress'],
    [/^\/admin-portal\/work-progress\/\d+\/reports\/$/, 'Daily Work Reports'],
    [/^\/admin-portal\/work-progress\/\d+\/evidence\/(\d+\/)?$/, 'Work Evidence'],
    [/^\/admin-portal\/complaints\/$/, 'Complaints'],
    [/^\/admin-portal\/complaints\/\d+\/$/, 'the case'],
    [/^\/admin-portal\/complaints\/\d+\/(customer|handyman)\/$/, 'the conversation'],
    [/^\/reviews\/admin\/$/, 'Private Feedback'],
    [/^\/reviews\/admin\/\d+\/$/, 'Feedback Details'],
    [/^\/reports\/job-summary\/$/, 'Reports']
  ];

  function labelFor(path) {
    for (var i = 0; i < PAGES.length; i++) {
      if (PAGES[i][0].test(path)) return PAGES[i][1];
    }
    return null;
  }

  var store;
  try { store = window.sessionStorage; store.getItem('x'); } catch (e) { return; }   // no storage: keep the links

  var here = location.pathname;
  var key = 'hc-back:' + here;
  var nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {};
  var viaBackLink = store.getItem('hc-back-nav') === here;
  store.removeItem('hc-back-nav');

  var saved = store.getItem(key);
  var target = saved;
  if (nav.type !== 'reload' && nav.type !== 'back_forward' && !viaBackLink) {
    var from = null;
    try { from = document.referrer ? new URL(document.referrer) : null; } catch (e) { from = null; }
    if (!from || from.origin !== location.origin) {
      target = null;                                   // opened from outside: the template's link
    } else if (from.pathname !== here && labelFor(from.pathname)) {
      target = from.pathname + from.search;            // came from another admin page
    }
    // else: the same page or a form page (after a save): keep what was saved
    if (target) store.setItem(key, target); else store.removeItem(key);
  }
  if (!target) return;

  var label = labelFor(target.split('?')[0]);
  if (!label) return;
  links.forEach(function (a) {
    a.href = target;
    a.textContent = '← Back to ' + label;
    a.addEventListener('click', function () {
      store.setItem('hc-back-nav', target.split('?')[0]);   // the page we go back to keeps its own back link
    });
  });
})();