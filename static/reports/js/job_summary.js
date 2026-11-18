/* Reports - Job Summary Report (admin).
   Pages through the rows on screen, and shows every row in the preview and on paper. */
(function () {
  var root = document.documentElement;
  var box = document.querySelector('[data-report]');

  if (box) {
    var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
    var size = parseInt(box.dataset.pageSize, 10) || 6;
    var count = box.querySelector('[data-count]');
    var pages = box.querySelector('[data-pages]');
    var current = 1;

    function button(label, page, opts) {
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
      var total = Math.max(1, Math.ceil(rows.length / size));
      var start = (current - 1) * size;
      rows.forEach(function (r, i) { r.classList.toggle('is-off', i < start || i >= start + size); });
      count.textContent = rows.length
        ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, rows.length) + ' of ' + rows.length + ' jobs · Preview and Print include every job'
        : '';
      pages.innerHTML = '';
      pages.hidden = total === 1;
      if (total === 1) return;
      pages.appendChild(button('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= total; i++) pages.appendChild(button(String(i), i));
      pages.appendChild(button('›', Math.min(total, current + 1), { aria: 'Next page', disabled: current === total, arrow: true }));
    }
    render();
  }

  // Preview: the report as it will print. Print: the same layout on paper.
  var previewing = false;
  function setPreview(on) {
    previewing = on;
    root.classList.toggle('rp-preview', on);
    window.scrollTo(0, 0);
  }
  document.querySelectorAll('[data-preview]').forEach(function (b) {
    b.addEventListener('click', function () { setPreview(true); });
  });
  document.querySelectorAll('[data-close-preview]').forEach(function (b) {
    b.addEventListener('click', function () { setPreview(false); });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && previewing) setPreview(false); });
  document.querySelectorAll('[data-print]').forEach(function (b) {
    b.addEventListener('click', function () { window.print(); });
  });
  // Printing from the browser menu (Ctrl+P) uses the same clean layout
  window.addEventListener('beforeprint', function () { root.classList.add('rp-preview'); });
  window.addEventListener('afterprint', function () { if (!previewing) root.classList.remove('rp-preview'); });
})();