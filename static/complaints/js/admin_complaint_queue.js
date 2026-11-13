/* Complaints - Complaint Queue (section 12).
   Status tabs, search, "submitted by", the date range, Clear Filters and
   the page buttons. They work on the rows already on the page. */
(function () {
  var box = document.querySelector('[data-queue]');
  if (!box) return;

  var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
  var tabs = Array.prototype.slice.call(box.querySelectorAll('[data-tab]'));
  var search = box.querySelector('[data-search]');
  var by = box.querySelector('[data-by]');
  var from = box.querySelector('[data-from]');
  var to = box.querySelector('[data-to]');
  var empty = box.querySelector('[data-empty]');
  var count = box.querySelector('[data-count]');
  var pages = box.querySelector('[data-pages]');
  var size = parseInt(box.dataset.pageSize, 10) || 5;
  var tab = '';
  var current = 1;

  function matches(row) {
    var q = search.value.trim().toLowerCase();
    // Dates are written as YYYY-MM-DD, so plain text comparison orders them correctly
    return (!tab || row.dataset.status === tab) &&
           (!q || row.dataset.text.indexOf(q) > -1) &&
           (!by.value || row.dataset.role === by.value) &&
           (!from.value || row.dataset.date >= from.value) &&
           (!to.value || row.dataset.date <= to.value);
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
    var totalPages = Math.max(1, Math.ceil(found.length / size));
    if (current > totalPages) current = totalPages;
    var start = (current - 1) * size;

    rows.forEach(function (row) { row.hidden = true; });
    found.slice(start, start + size).forEach(function (row) { row.hidden = false; });

    empty.hidden = found.length !== 0;
    count.textContent = found.length
      ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, found.length) +
        ' of ' + found.length + ' complaint' + (found.length === 1 ? '' : 's') + ' · Newest first'
      : '';

    tabs.forEach(function (t) { t.setAttribute('aria-pressed', t.dataset.tab === tab ? 'true' : 'false'); });

    pages.innerHTML = '';
    pages.hidden = totalPages === 1;
    if (totalPages === 1) return;
    pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
    for (var i = 1; i <= totalPages; i++) pages.appendChild(pageButton(String(i), i));
    pages.appendChild(pageButton('›', Math.min(totalPages, current + 1), { aria: 'Next page', disabled: current === totalPages, arrow: true }));
  }

  function filtersChanged() { current = 1; render(); }

  tabs.forEach(function (t) {
    t.addEventListener('click', function () { tab = t.dataset.tab; filtersChanged(); });
  });
  search.addEventListener('input', filtersChanged);
  by.addEventListener('change', filtersChanged);
  from.addEventListener('change', filtersChanged);
  to.addEventListener('change', filtersChanged);

  box.querySelector('[data-clear]').addEventListener('click', function () {
    tab = ''; search.value = ''; by.value = ''; from.value = ''; to.value = '';
    filtersChanged();
  });

  render();
})();