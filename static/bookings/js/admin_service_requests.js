/* Manage Service Requests (FR-A-4).
   1. List: search, the service / status / date filters, Clear Filters and the page buttons.
      They work on the rows already on the page (5 per page).
   2. Details: pop-ups ([data-open] opens, [data-close] closes; "?response=1" opens the
      handyman's answer straight away) and the demo forms (form[data-demo]: nothing is saved yet).
      BACKEND: remove data-demo from a form once its view exists. */
(function () {
  /* ---------- 1. List ---------- */
  var box = document.querySelector('[data-requests]');
  if (box) {
    var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
    var search = box.querySelector('[data-search]');
    var service = box.querySelector('[data-service]');
    var status = box.querySelector('[data-status]');
    var date = box.querySelector('[data-date]');
    var empty = box.querySelector('[data-empty]');
    var count = box.querySelector('[data-count]');
    var pages = box.querySelector('[data-pages]');
    var size = parseInt(box.dataset.pageSize, 10) || 5;
    var current = 1;
    var today = new Date(); today.setHours(0, 0, 0, 0);

    function age(row) {   // days since the request was received
      var p = row.dataset.date.split('-');
      return Math.round((today - new Date(+p[0], +p[1] - 1, +p[2])) / 86400000);
    }

    function matches(row) {
      var q = search.value.trim().toLowerCase();
      var d = date.value, days = age(row);
      return (!q || row.dataset.text.indexOf(q) > -1) &&
             (!service.value || row.dataset.service === service.value) &&
             (!status.value || row.dataset.status === status.value) &&
             (!d || (d === 'old' ? days > 30 : days <= +d));
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
          ' request' + (found.length === 1 ? '' : 's') + ' · Newest first'
        : '';
      pages.innerHTML = '';
      pages.hidden = total === 1;
      if (total === 1) return;
      pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= total; i++) pages.appendChild(pageButton(String(i), i));
      pages.appendChild(pageButton('›', Math.min(total, current + 1), { aria: 'Next page', disabled: current === total, arrow: true }));
    }

    function changed() { current = 1; render(); }
    search.addEventListener('input', changed);
    [service, status, date].forEach(function (s) { s.addEventListener('change', changed); });
    box.querySelector('[data-clear]').addEventListener('click', function () {
      search.value = ''; service.value = ''; status.value = ''; date.value = '';
      changed();
    });
    render();
  }

  /* ---------- 2. Details: pop-ups and demo forms ---------- */
  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var from = btn.closest('dialog');
      if (from) from.close();             // a button inside a pop-up opens the next one
      var d = document.getElementById(btn.dataset.open);
      if (d) d.showModal();
    });
  });
  document.querySelectorAll('.ql-modal').forEach(function (d) {
    d.querySelectorAll('[data-close]:not([data-open])').forEach(function (b) {
      b.addEventListener('click', function () { d.close(); });
    });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });
  var auto = document.querySelector('[data-auto-open]');
  if (auto) {
    auto.showModal();
    history.replaceState(null, '', location.pathname);
  }

  var msg = document.querySelector('[data-demo-msg]');
  document.querySelectorAll('form[data-demo]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var d = form.closest('dialog');
      if (d) d.close();
      if (msg) { msg.firstElementChild.textContent = form.getAttribute('data-demo'); msg.hidden = false; }
    });
  });
})();