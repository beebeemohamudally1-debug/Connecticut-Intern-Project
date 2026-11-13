/* Monitor Work Progress - Overview (section 5).
   Search, the two filters, Clear Filters and the page buttons.
   They work on the rows already on the page. */
(function () {
  var box = document.querySelector('[data-jobs]');
  if (!box) return;

  var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
  var search = box.querySelector('[data-search]');
  var service = box.querySelector('[data-service]');
  var status = box.querySelector('[data-status]');
  var empty = box.querySelector('[data-empty]');
  var count = box.querySelector('[data-count]');
  var pages = box.querySelector('[data-pages]');
  var size = parseInt(box.dataset.pageSize, 10) || 6;
  var current = 1;

  function matches(row) {
    var q = search.value.trim().toLowerCase();
    return (!q || row.dataset.text.indexOf(q) > -1) &&
           (!service.value || row.dataset.service === service.value) &&
           (!status.value || row.dataset.status === status.value);
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
        ' of ' + found.length + ' assigned job' + (found.length === 1 ? '' : 's')
      : '';

    pages.innerHTML = '';
    pages.hidden = totalPages === 1;
    if (totalPages === 1) return;
    pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
    for (var i = 1; i <= totalPages; i++) pages.appendChild(pageButton(String(i), i));
    pages.appendChild(pageButton('›', Math.min(totalPages, current + 1), { aria: 'Next page', disabled: current === totalPages, arrow: true }));
  }

  function filtersChanged() { current = 1; render(); }

  search.addEventListener('input', filtersChanged);
  service.addEventListener('change', filtersChanged);
  status.addEventListener('change', filtersChanged);

  box.querySelector('[data-clear]').addEventListener('click', function () {
    search.value = ''; service.value = ''; status.value = '';
    filtersChanged();
  });

  render();
})();