/* Service Quotations - Labour estimates and Quotations tabs (admin).
   Fills the number cards and the customer filter from the rows, and runs the review pop-ups.
   Load it before admin_labour_quotations.js (search, filters and pages). */
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll('[data-row]'));

  // Number cards: count the rows by status
  document.querySelectorAll('[data-stat]').forEach(function (el) {
    var n = rows.filter(function (r) { return r.dataset.status === el.dataset.stat; }).length;
    el.textContent = n < 10 ? '0' + n : String(n);
  });

  // Customer filter: one option per customer on the page
  var select = document.querySelector('[data-customer]');
  if (select) {
    var names = [];
    rows.forEach(function (r) { if (names.indexOf(r.dataset.customer) === -1) names.push(r.dataset.customer); });
    names.sort().forEach(function (name) {
      var o = document.createElement('option');
      o.value = name; o.textContent = name;
      select.appendChild(o);
    });
    rows.forEach(function (r) { r.dataset.text = r.dataset.text.toLowerCase(); });
  }

  // Empty list: show the message straight away
  if (!rows.length) {
    var empty = document.querySelector('[data-empty]');
    if (empty) empty.hidden = false;
  }

  // Pop-ups
  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = document.getElementById(btn.dataset.open);
      if (d) d.showModal();
    });
  });
  document.querySelectorAll('.ql-modal').forEach(function (d) {
    d.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });

  // A link ending in #est-<id> (e.g. from Service Request Details) opens that estimate's pop-up
  var linked = location.hash && document.getElementById(location.hash.slice(1));
  if (linked && linked.classList.contains('ql-modal')) {
    linked.showModal();
    history.replaceState(null, '', location.pathname + location.search);
  }

  // Review: a note is needed to reject or ask for a revision
  document.querySelectorAll('[data-review]').forEach(function (form) {
    var note = form.querySelector('textarea[name="note"]');
    var error = form.querySelector('[data-error]');
    if (!note) return;
    note.addEventListener('input', function () { note.removeAttribute('aria-invalid'); error.hidden = true; });
    form.addEventListener('submit', function (e) {
      var action = e.submitter ? e.submitter.value : '';
      if ((action === 'reject' || action === 'revision') && !note.value.trim()) {
        e.preventDefault();
        note.setAttribute('aria-invalid', 'true');
        error.hidden = false;
        note.focus();
      }
    });
  });
})();