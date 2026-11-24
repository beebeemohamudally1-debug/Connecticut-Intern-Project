/* Appointments (admin).
   1. Manage Appointments: type tabs, search, filters and page buttons on the rows already on the page.
   2. Schedule / Reschedule: checks the chosen handyman, date and slot against the confirmed bookings
      sent by the view, and shows the result before the form is sent (the server checks again).
   3. Confirm / Cancel pop-ups (form[data-demo]): nothing is saved yet, so they close and show a demo
      message. BACKEND: remove data-demo from the form once its view exists.
   Pop-ups ([data-open], .ql-modal) are run by payments/js/admin_quotation_lists.js. */
(function () {
  /* ---------- 1. Manage Appointments ---------- */
  var box = document.querySelector('[data-appointments]');
  if (box) {
    var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
    var tabs = Array.prototype.slice.call(box.querySelectorAll('[data-type]')).filter(function (b) { return b.tagName === 'BUTTON'; });
    var search = box.querySelector('[data-search]');
    var status = box.querySelector('[data-status]');
    var dateSel = box.querySelector('[data-date]');
    var handyman = box.querySelector('[data-handyman]');
    var empty = box.querySelector('[data-empty]');
    var count = box.querySelector('[data-count]');
    var pages = box.querySelector('[data-pages]');
    var size = parseInt(box.dataset.pageSize, 10) || 6;
    var type = '';
    var current = 1;
    var today = new Date(); today.setHours(0, 0, 0, 0);

    rows.forEach(function (r) { r.dataset.text = r.dataset.text.toLowerCase(); });

    function days(row) { return Math.round((new Date(row.dataset.date + 'T00:00:00') - today) / 86400000); }

    function dateOk(row) {
      var d = days(row);
      switch (dateSel.value) {
        case 'today': return d === 0;
        case 'week': return d >= 0 && d <= 7;
        case 'upcoming': return d >= 0;
        case 'past': return d < 0;
        default: return true;
      }
    }

    function matches(row) {
      var q = search.value.trim().toLowerCase();
      return (!type || row.dataset.type === type) &&
             (!status.value || row.dataset.status === status.value) &&
             (!handyman.value || row.dataset.handyman === handyman.value) &&
             dateOk(row) && (!q || row.dataset.text.indexOf(q) > -1);
    }

    function pageButton(label, page, extra) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = label;
      if (extra && extra.aria) btn.setAttribute('aria-label', extra.aria);
      if (extra && extra.disabled) btn.disabled = true;
      if (page === current && !(extra && extra.arrow)) btn.setAttribute('aria-current', 'page');
      btn.addEventListener('click', function () { current = page; render(); });
      return btn;
    }

    function render() {
      var found = rows.filter(matches);
      var total = Math.max(1, Math.ceil(found.length / size));
      if (current > total) current = total;
      var start = (current - 1) * size;
      rows.forEach(function (r) { r.hidden = true; });
      found.slice(start, start + size).forEach(function (r) { r.hidden = false; });
      empty.hidden = found.length !== 0;
      count.textContent = found.length
        ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, found.length) + ' of ' + found.length +
          ' appointment' + (found.length === 1 ? '' : 's') + ' · Latest date first'
        : '';
      pages.innerHTML = '';
      pages.hidden = total === 1;
      if (total === 1) return;
      pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= total; i++) pages.appendChild(pageButton(String(i), i));
      pages.appendChild(pageButton('›', Math.min(total, current + 1), { aria: 'Next page', disabled: current === total, arrow: true }));
    }

    function changed() { current = 1; render(); }
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        type = tab.dataset.type;
        tabs.forEach(function (t) { t.setAttribute('aria-pressed', String(t === tab)); });
        changed();
      });
    });
    search.addEventListener('input', changed);
    [status, dateSel, handyman].forEach(function (el) { el.addEventListener('change', changed); });
    box.querySelector('[data-clear]').addEventListener('click', function () {
      search.value = ''; status.value = ''; dateSel.value = ''; handyman.value = '';
      changed();
    });
    render();
  }

  /* ---------- 2. Schedule / Reschedule: live availability ---------- */
  var slotForm = document.querySelector('[data-slot-form]');
  if (slotForm) {
    var busy = JSON.parse(document.getElementById('busy-data').textContent);
    var who = slotForm.querySelector('[name="handyman"]');
    var fixed = slotForm.dataset.handyman;
    var day = slotForm.querySelector('[name="date"]');
    var slot = slotForm.querySelector('[name="slot"]');
    var out = slotForm.querySelector('[data-availability]');

    function check() {
      var h = who ? who.value : fixed;
      if (!h || !day.value || !slot.value) {
        out.textContent = 'Choose the date and slot to check availability.';
        out.className = 'ap-avail';
        return;
      }
      var clash = busy.filter(function (b) { return String(b.handyman) === String(h) && b.date === day.value && b.slot === slot.value; })[0];
      out.textContent = clash ? 'Not available: ' + clash.ref + ' is already confirmed in this slot.' : 'Available: no confirmed booking in this slot.';
      out.className = 'ap-avail ' + (clash ? 'is-busy' : 'is-free');
    }
    [who, day, slot].forEach(function (el) { if (el) el.addEventListener('change', check); });
    check();
  }

  /* Request picker on the Schedule page: load the chosen request */
  var picker = document.querySelector('[data-request-picker]');
  if (picker) picker.addEventListener('change', function () { if (picker.value) picker.form.submit(); });

  /* ---------- 3. Demo pop-up forms (no backend view yet) ---------- */
  var msg = document.querySelector('[data-demo-msg]');
  Array.prototype.forEach.call(document.querySelectorAll('form[data-demo]'), function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var dlg = form.closest('dialog');
      if (dlg) dlg.close();
      if (msg) { msg.firstElementChild.textContent = form.getAttribute('data-demo'); msg.hidden = false; }
      var next = document.getElementById(form.getAttribute('data-demo-next') || '');
      if (next) next.showModal();
    });
  });
})();