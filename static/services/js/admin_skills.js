/* Manage Skills (admin).
   1. Lists (Skills, Skill Requests): search, the two filters, Clear Filters and the page buttons.
      They work on the rows already on the page (data-page-size per page).
   2. Pop-ups: [data-open] opens a <dialog class="ql-modal">, [data-close] closes it.
   3. Add / Edit form: the name is needed and must not be used by another skill.
   4. Decision form: a note is needed to reject.
   Forms with data-demo save nothing yet: they show a demo message instead.
   BACKEND: remove data-demo from a form once its view exists. */
(function () {
  /* ---------- 1. Lists ---------- */
  var box = document.querySelector('[data-skills]');
  if (box) {
    var rows = Array.prototype.slice.call(box.querySelectorAll('[data-row]'));
    var search = box.querySelector('[data-search]');
    var category = box.querySelector('[data-category]');
    var status = box.querySelector('[data-status]');
    var empty = box.querySelector('[data-empty]');
    var count = box.querySelector('[data-count]');
    var pages = box.querySelector('[data-pages]');
    var size = parseInt(box.dataset.pageSize, 10) || 5;
    var noun = box.dataset.noun || 'skill';
    var current = 1;

    var matches = function (row) {
      var q = search.value.trim().toLowerCase();
      return (!q || row.dataset.text.indexOf(q) > -1) &&
             (!category.value || row.dataset.category === category.value) &&
             (!status.value || row.dataset.status === status.value);
    };

    var pageButton = function (label, page, extra) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = label;
      if (extra && extra.aria) btn.setAttribute('aria-label', extra.aria);
      if (extra && extra.disabled) btn.disabled = true;
      if (page === current && !(extra && extra.arrow)) btn.setAttribute('aria-current', 'page');
      btn.addEventListener('click', function () { current = page; render(); });
      return btn;
    };

    var render = function () {
      var found = rows.filter(matches);
      var total = Math.max(1, Math.ceil(found.length / size));
      if (current > total) current = total;
      var start = (current - 1) * size;
      rows.forEach(function (r) { r.hidden = true; });
      found.slice(start, start + size).forEach(function (r) { r.hidden = false; });
      empty.hidden = found.length !== 0;
      count.textContent = found.length
        ? 'Showing ' + (start + 1) + '–' + Math.min(start + size, found.length) + ' of ' + found.length +
          ' ' + noun + (found.length === 1 ? '' : 's')
        : '';
      pages.innerHTML = '';
      pages.hidden = total === 1;
      if (total === 1) return;
      pages.appendChild(pageButton('‹', Math.max(1, current - 1), { aria: 'Previous page', disabled: current === 1, arrow: true }));
      for (var i = 1; i <= total; i++) pages.appendChild(pageButton(String(i), i));
      pages.appendChild(pageButton('›', Math.min(total, current + 1), { aria: 'Next page', disabled: current === total, arrow: true }));
    };

    var changed = function () { current = 1; render(); };
    search.addEventListener('input', changed);
    [category, status].forEach(function (s) { s.addEventListener('change', changed); });
    box.querySelector('[data-clear]').addEventListener('click', function () {
      search.value = ''; category.value = ''; status.value = '';
      changed();
    });
    render();
  }

  /* ---------- 2. Pop-ups ---------- */
  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = document.getElementById(btn.dataset.open);
      if (d) d.showModal();
    });
  });
  document.querySelectorAll('.ql-modal').forEach(function (d) {
    d.querySelectorAll('[data-close]').forEach(function (b) {
      b.addEventListener('click', function () { d.close(); });
    });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });

  /* Demo message (nothing is saved yet) */
  var msg = document.querySelector('[data-demo-msg]');
  function demo(form) {
    var d = form.closest('dialog');
    if (d) d.close();
    if (msg) {
      msg.firstElementChild.textContent = form.getAttribute('data-demo');
      msg.hidden = false;
    }
  }
  function showError(input, el, text) {
    input.setAttribute('aria-invalid', text ? 'true' : 'false');
    el.textContent = text || '';
    el.hidden = !text;
  }

  /* ---------- 3. Add / Edit form ---------- */
  var skillForm = document.querySelector('[data-skill-form]');
  if (skillForm) {
    var nameInput = skillForm.querySelector('[data-name]');
    var nameErr = skillForm.querySelector('[data-err-name]');
    var listEl = document.getElementById('skill-names');
    var taken = (listEl ? JSON.parse(listEl.textContent) : []).map(function (n) { return n.trim().toLowerCase(); });

    var checkName = function () {
      var v = nameInput.value.trim();
      var text = !v ? 'Please enter a skill name.'
        : taken.indexOf(v.toLowerCase()) > -1 ? 'A skill with this name already exists.' : '';
      showError(nameInput, nameErr, text);
      return !text;
    };
    nameInput.addEventListener('input', function () { if (nameInput.getAttribute('aria-invalid') === 'true') checkName(); });
    skillForm.addEventListener('submit', function (e) {
      if (!checkName()) { e.preventDefault(); nameInput.focus(); return; }
      if (skillForm.hasAttribute('data-demo')) { e.preventDefault(); demo(skillForm); }
    });
  }

  /* ---------- 4. Decision form (Approve / Reject) ---------- */
  var decision = document.querySelector('[data-decision]');
  if (decision) {
    var note = decision.querySelector('[data-note]');
    var noteErr = decision.querySelector('[data-err-note]');
    note.addEventListener('input', function () { if (note.value.trim()) showError(note, noteErr, ''); });
    decision.addEventListener('submit', function (e) {
      var rejecting = e.submitter && e.submitter.value === 'reject';
      if (rejecting && !note.value.trim()) {
        e.preventDefault();
        showError(note, noteErr, 'Please give a reason before rejecting.');
        note.focus();
        return;
      }
      if (decision.hasAttribute('data-demo')) { e.preventDefault(); demo(decision); }
    });
  }

  /* ---------- Other demo forms (Deactivate / Reactivate pop-up) ---------- */
  document.querySelectorAll('form[data-demo]').forEach(function (form) {
    if (form === skillForm || form === decision) return;
    form.addEventListener('submit', function (e) { e.preventDefault(); demo(form); });
  });
})();