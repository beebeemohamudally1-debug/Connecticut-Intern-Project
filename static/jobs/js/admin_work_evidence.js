/* Monitor Work Progress - Work Evidence (section 5).
   Shows the photographs 3 at a time. The page buttons only appear when
   there are more than 3 photos. */
(function () {
  var box = document.querySelector('[data-photos]');
  if (!box) return;

  var items = Array.prototype.slice.call(box.querySelectorAll('[data-item]'));
  var foot = box.querySelector('[data-foot]');
  var count = box.querySelector('[data-count]');
  var pages = box.querySelector('[data-pages]');
  var size = parseInt(box.dataset.pageSize, 10) || 3;
  var current = 1;

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
    var totalPages = Math.max(1, Math.ceil(items.length / size));
    if (current > totalPages) current = totalPages;
    var start = (current - 1) * size;

    items.forEach(function (item) { item.hidden = true; });
    items.slice(start, start + size).forEach(function (item) { item.hidden = false; });

    foot.hidden = totalPages === 1;
    if (totalPages === 1) return;

    count.textContent = 'Showing ' + (start + 1) + '–' + Math.min(start + size, items.length) +
      ' of ' + items.length + ' photos';
    pages.innerHTML = '';
    pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
    for (var i = 1; i <= totalPages; i++) pages.appendChild(pageButton(String(i), i));
    pages.appendChild(pageButton('›', Math.min(totalPages, current + 1), { aria: 'Next page', disabled: current === totalPages, arrow: true }));
  }

  render();
})();


/* The Flag pop-up: open, close, check the reason, then send it to jobs:flag. */
(function () {
  var modal = document.getElementById('modal-flag');
  if (!modal) return;

  var form = modal.querySelector('[data-flag-form]');
  var reason = modal.querySelector('[data-reason]');
  var error = modal.querySelector('[data-error]');

  function open() { modal.showModal(); if (reason) reason.focus(); }

  document.querySelectorAll('[data-open="flag"]').forEach(function (btn) {
    btn.addEventListener('click', open);
  });

  // The Job Progress Details page links here with #flag to open the pop-up
  if (location.hash === '#flag') open();

  modal.querySelectorAll('[data-close]').forEach(function (btn) {
    btn.addEventListener('click', function () { modal.close(); });
  });

  // Clicking the dark area outside the pop-up also closes it
  modal.addEventListener('click', function (e) { if (e.target === modal) modal.close(); });

  if (reason) {
    reason.addEventListener('input', function () {
      error.hidden = true;
      reason.removeAttribute('aria-invalid');
    });
  }

  form.addEventListener('submit', function (e) {
    // A reason is required to flag (the backend checks it too)
    if (reason && !reason.value.trim()) {
      e.preventDefault();
      error.hidden = false;
      reason.setAttribute('aria-invalid', 'true');
      reason.focus();
      return;
    }
  });
})();
