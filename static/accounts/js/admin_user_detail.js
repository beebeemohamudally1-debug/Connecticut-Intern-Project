/* Customer Details, Handyman Profile and Registration Verification.
   - Buttons with data-open open the pop-up with that name.
   - Buttons with data-close close it.
   - Confirm and Approve/Reject only show a demo message for now.
   - Lists with data-paged get page buttons. */
(function () {
  var demo = document.querySelector('[data-demo]');

  function say(text) {
    if (!demo) return;
    demo.textContent = text;
    demo.hidden = false;
  }

  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var box = document.getElementById('modal-' + btn.dataset.open);
      if (box) box.showModal();
    });
  });

  document.querySelectorAll('dialog [data-close]').forEach(function (btn) {
    btn.addEventListener('click', function () { btn.closest('dialog').close(); });
  });

  // Clicking the dark area outside the pop-up also closes it
  document.querySelectorAll('dialog').forEach(function (box) {
    box.addEventListener('click', function (e) { if (e.target === box) box.close(); });
  });

  document.querySelectorAll('dialog [data-confirm]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('dialog').close();
      say('Account ' + btn.dataset.confirm + ' (frontend demo only, nothing is saved yet).');
    });
  });

  document.querySelectorAll('[data-decide]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      say('Registration ' + btn.dataset.decide + ' (frontend demo only, nothing is saved yet).');
    });
  });

  // Pages for a list: items with data-paged, buttons go in [data-list-pages]
  document.querySelectorAll('[data-paged]').forEach(function (list) {
    var items = Array.prototype.slice.call(list.children);
    var size = parseInt(list.dataset.pageSize, 10) || 3;
    var nav = list.parentNode.querySelector('[data-list-pages]');
    var total = Math.ceil(items.length / size);
    var current = 1;
    if (!nav || total < 2) return;

    function button(label, page, aria, off) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      if (aria) b.setAttribute('aria-label', aria);
      if (off) b.disabled = true;
      if (!aria && page === current) b.setAttribute('aria-current', 'page');
      b.addEventListener('click', function () { current = page; show(); });
      return b;
    }

    function show() {
      items.forEach(function (li, i) {
        li.hidden = i < (current - 1) * size || i >= current * size;
      });
      nav.innerHTML = '';
      nav.appendChild(button('\u2039', current - 1, 'Previous page', current === 1));
      for (var p = 1; p <= total; p++) nav.appendChild(button(String(p), p));
      nav.appendChild(button('\u203A', current + 1, 'Next page', current === total));
    }
    show();
  });
})();