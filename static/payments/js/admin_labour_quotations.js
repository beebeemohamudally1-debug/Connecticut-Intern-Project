/* Labour Quotations - Overview (section 6).
   Search, the customer and status filters, Clear Filters and the page buttons. They work on the rows already on the page. */
(function () {
  var box = document.querySelector('[data-queue]');
  if (!box) return;

  var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
  var search = box.querySelector('[data-search]');
  var customer = box.querySelector('[data-customer]');
  var empty = box.querySelector('[data-empty]');
  var count = box.querySelector('[data-count]');
  var pages = box.querySelector('[data-pages]');
  var size = parseInt(box.dataset.pageSize, 10) || 5;
  var status = box.querySelector('[data-status]');
  var noun = box.dataset.noun || 'quotation';
  var current = 1;

  function matches(row) {
    var q = search.value.trim().toLowerCase();
    return (!status.value || row.dataset.status === status.value) &&
           (!q || row.dataset.text.indexOf(q) > -1) &&
           (!customer.value || row.dataset.customer === customer.value);
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
        ' of ' + found.length + ' ' + noun + (found.length === 1 ? '' : 's') + ' · Latest update first'
      : '';

    pages.innerHTML = '';
    pages.hidden = totalPages === 1;
    if (totalPages === 1) return;
    pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
    for (var i = 1; i <= totalPages; i++) pages.appendChild(pageButton(String(i), i));
    pages.appendChild(pageButton('›', Math.min(totalPages, current + 1), { aria: 'Next page', disabled: current === totalPages, arrow: true }));
  }

  function filtersChanged() { current = 1; render(); }

  status.addEventListener('change', filtersChanged);
  search.addEventListener('input', filtersChanged);
  customer.addEventListener('change', filtersChanged);

  box.querySelector('[data-clear]').addEventListener('click', function () {
    status.value = ''; search.value = ''; customer.value = '';
    filtersChanged();
  });

  render();
})();

/* After Approve: the page reloads, so the estimate is remembered for one load and a pop-up
   offers its Prepare quote link (the same link as the row's button). */
(function () {
  var KEY = 'hc-approved-estimate';
  document.querySelectorAll('[data-review] button[value="approve"]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var dlg = btn.closest('dialog');
      try { sessionStorage.setItem(KEY, dlg.id.replace('est-', '')); } catch (e) {}
    });
  });

  var id = null;
  try { id = sessionStorage.getItem(KEY); sessionStorage.removeItem(KEY); } catch (e) {}
  var modal = document.getElementById('est-approved');
  if (!id || !modal || !document.querySelector('.ql-msg')) return;
  var row = document.querySelector('[data-row][data-estimate="' + id + '"]');
  var link = row && row.dataset.status === 'ready' && row.querySelector('a[href*="quotations/new"]');
  if (!link) return;
  modal.querySelector('[data-approved-text]').textContent =
    row.querySelector('.lq-id').textContent + ' is ready for a quotation. Prepare it now?';
  modal.querySelector('[data-approved-link]').href = link.href;
  modal.showModal();
})();
