/* Private Feedback (admin).
   List: search, date filter, Clear Filters and the page buttons, on the rows already on the page.
   Details: the Approve and Reject confirmation pop-ups. */
(function () {
  var box = document.querySelector('[data-reviews]');
  if (box) {
    var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
    var search = box.querySelector('[data-search]');
    var days = box.querySelector('[data-days]');
    var empty = box.querySelector('[data-empty]');
    var count = box.querySelector('[data-count]');
    var pages = box.querySelector('[data-pages]');
    var size = parseInt(box.dataset.pageSize, 10) || 5;
    var current = 1;
    rows.forEach(function (r) { r.dataset.text = r.dataset.text.toLowerCase(); });

    function matches(row) {
      var q = search.value.trim().toLowerCase();
      if (q && row.dataset.text.indexOf(q) === -1) return false;
      if (days.value) {
        var since = new Date();
        since.setHours(0, 0, 0, 0);
        since.setDate(since.getDate() - parseInt(days.value, 10));
        if (new Date(row.dataset.date + 'T00:00:00') < since) return false;
      }
      return true;
    }

    function pageButton(label, page, opts) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      if (opts && opts.aria) b.setAttribute('aria-label', opts.aria);
      if (opts && opts.disabled) b.disabled = true;
      if (page === current && !(opts && opts.arrow)) b.setAttribute('aria-current', 'page');
      b.addEventListener('click', function () { current = page; render(); });
      return b;
    }

    function render() {
      var found = rows.filter(matches);
      var total = Math.max(1, Math.ceil(found.length / size));
      if (current > total) current = total;
      var start = (current - 1) * size;
      rows.forEach(function (r) { r.hidden = true; });
      found.slice(start, start + size).forEach(function (r) { r.hidden = false; });
      if (rows.length) empty.hidden = found.length !== 0;
      count.textContent = found.length
        ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, found.length) + ' of ' + found.length +
          ' feedback · Newest first'
        : '';
      pages.innerHTML = '';
      pages.hidden = total === 1;
      if (total === 1) return;
      pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= total; i++) pages.appendChild(pageButton(String(i), i));
      pages.appendChild(pageButton('›', Math.min(total, current + 1), { aria: 'Next page', disabled: current === total, arrow: true }));
    }

    search.addEventListener('input', function () { current = 1; render(); });
    days.addEventListener('change', function () { current = 1; render(); });
    box.querySelector('[data-clear]').addEventListener('click', function () {
      search.value = ''; days.value = ''; current = 1; render();
    });
    render();
  }

  // Details: confirmation pop-ups
  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = document.getElementById(btn.dataset.open);
      if (d) d.showModal();
    });
  });
  document.querySelectorAll('.rv-modal').forEach(function (d) {
    d.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });
})();