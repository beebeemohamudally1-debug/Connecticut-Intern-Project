/*
  Administrator Notifications (browser only).
  - Filter buttons show All, Unread, Read, or one kind of notification.
  - The counts on the buttons are worked out here, from the items on the page.
  - 5 items per page, with page buttons.
  - "Mark all as read" and clicking an item mark it as read for now.
  - Reading is also saved on the server: POST to the item's data-read-url, and
    to the box's data-read-all-url for "Mark all as read" (notifications app).
*/
(function () {
  var box = document.querySelector('[data-notifications]');
  if (!box) return;

  var items = Array.prototype.slice.call(box.querySelectorAll('[data-item]'));
  var filterBtns = Array.prototype.slice.call(document.querySelectorAll('[data-filter]'));
  var markAll = document.querySelector('[data-mark-all]');
  var title = document.querySelector('[data-title]');
  var summary = document.querySelector('[data-summary]');
  var empty = box.querySelector('[data-empty]');
  var showing = box.querySelector('[data-showing]');
  var pages = box.querySelector('[data-pages]');
  var size = parseInt(box.dataset.pageSize, 10) || 5;
  var filter = 'all';
  var current = 1;
  var csrf = box.dataset.csrf || '';

  function isUnread(item) { return item.dataset.read === '0'; }

  function matches(item, key) {
    if (key === 'all') return true;
    if (key === 'unread') return isUnread(item);
    if (key === 'read') return !isUnread(item);
    return item.dataset.kind === key;
  }

  function updateCounts() {
    filterBtns.forEach(function (btn) {
      var key = btn.dataset.filter;
      var n = items.filter(function (item) { return matches(item, key); }).length;
      var badge = btn.querySelector('[data-count]');
      if (badge) badge.textContent = n;
    });
    var unread = items.filter(isUnread).length;
    if (summary) summary.textContent = unread + ' unread notification' + (unread === 1 ? '' : 's') + ' · Important updates, all in one place.';
    if (title) title.textContent = unread ? 'You’re up to date. Almost.' : 'You’re all caught up.';
    if (markAll) markAll.disabled = unread === 0;
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
    var found = items.filter(function (item) { return matches(item, filter); });
    var totalPages = Math.max(1, Math.ceil(found.length / size));
    if (current > totalPages) current = totalPages;
    var start = (current - 1) * size;

    items.forEach(function (item) { item.hidden = true; });
    found.slice(start, start + size).forEach(function (item) { item.hidden = false; });

    empty.hidden = found.length !== 0;
    showing.textContent = found.length
      ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, found.length) + ' of ' + found.length + ' notifications'
      : '';

    pages.innerHTML = '';
    pages.hidden = totalPages === 1;
    if (totalPages > 1) {
      pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= totalPages; i++) pages.appendChild(pageButton(String(i), i));
      pages.appendChild(pageButton('›', Math.min(totalPages, current + 1), { aria: 'Next page', disabled: current === totalPages, arrow: true }));
    }
    updateCounts();
  }

  // Tell the server. The page already shows the change, so a failure only warns in the console.
  function save(url) {
    if (!url) return;
    fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrf }, credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) console.warn('Could not save read state (' + r.status + ')'); })
      .catch(function () { console.warn('Could not save read state'); });
  }

  function setRead(item) {
    item.dataset.read = '1';
    item.classList.remove('unread');
    var state = item.querySelector('[data-state]');
    if (state) state.textContent = 'Read';
  }

  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      filter = btn.dataset.filter;
      current = 1;
      filterBtns.forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
      render();
    });
  });

  items.forEach(function (item) {
    item.addEventListener('click', function () {
      if (isUnread(item)) { setRead(item); save(item.dataset.readUrl); render(); }
    });
  });

  if (markAll) {
    markAll.addEventListener('click', function () {
      items.forEach(setRead);
      save(box.dataset.readAllUrl);
      render();
    });
  }

  render();
})();