/* HandyConnect customer portal: behaviour for every customer page.
   Plain JS, no dependencies. Everything is opt-in through data-* attributes, so a page
   without the matching markup simply does nothing.

   data-cp-shell ............ the shell (mobile drawer, breadcrumb, initials)
   data-cp-form-steps ....... request form: marks step 1/2/3 as the form is filled
   data-cp-count="id" ....... textarea with a live character counter in #id (uses maxlength)
   data-cp-upload ........... file input wrapper: shows chosen file names, drag highlight, size check
   data-cp-stars ............ star rating radios, shows the chosen label
   data-cp-confirm="text" ... on a form/button: asks before submitting (uses #cp-confirm dialog)
   data-cp-search ........... live service search (fetches the existing services:search JSON endpoint)
   data-cp-tabs ............. client-side tab filter for [data-cp-tab] rows
   data-cp-print ............ button that calls window.print()
   data-cp-copy="text" ...... copies text to the clipboard
*/
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- Shell: drawer, breadcrumb, initials, dismissible messages ---------- */
  var root = $('[data-cp-shell]');
  if (root) {
    var burger = $('[data-cp-open-nav]');
    var setNav = function (open) {
      root.classList.toggle('is-nav-open', open);
      if (burger) burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    };
    if (burger) burger.addEventListener('click', function () { setNav(!root.classList.contains('is-nav-open')); });
    $$('[data-cp-close-nav]').forEach(function (e) { e.addEventListener('click', function () { setNav(false); }); });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      setNav(false);
      $$('[data-cp-menu][open]').forEach(function (d) { d.removeAttribute('open'); });
    });
    window.addEventListener('resize', function () { if (window.innerWidth > 1023) setNav(false); });
    document.addEventListener('click', function (e) {
      $$('[data-cp-menu][open]').forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute('open'); });
    });
    var active = $('.cp-nav a.is-active');
    var crumb = $('[data-cp-crumb]');
    if (active && crumb) crumb.textContent = active.textContent.replace(/\d+\s*$/, '').trim();
    var av = $('[data-cp-initials]'), nm = $('.cp-user-name');
    if (av && nm && !av.getAttribute('data-keep')) {
      var parts = nm.textContent.trim().split(/\s+/);
      av.textContent = ((parts[0] || '')[0] || '') + ((parts.length > 1 ? parts[parts.length - 1] : '')[0] || '');
    }
    $$('[data-cp-dismiss]').forEach(function (b) { b.addEventListener('click', function () { b.parentNode.remove(); }); });
  }

  /* ---------- Character counter ---------- */
  $$('[data-cp-count]').forEach(function (ta) {
    var out = document.getElementById(ta.getAttribute('data-cp-count'));
    if (!out) return;
    var max = ta.getAttribute('maxlength');
    var upd = function () { out.textContent = ta.value.length + (max ? ' / ' + max : ''); };
    ta.addEventListener('input', upd); upd();
  });

  /* ---------- File inputs ---------- */
  $$('[data-cp-upload]').forEach(function (box) {
    var input = $('input[type=file]', box), names = $('.cp-upload-names', box);
    if (!input) return;
    var maxMb = parseFloat(box.getAttribute('data-max-mb') || '10');
    var show = function () {
      var list = Array.prototype.slice.call(input.files || []);
      var big = list.filter(function (f) { return f.size > maxMb * 1048576; });
      if (big.length) {
        input.value = '';
        if (names) names.textContent = 'Each file must be under ' + maxMb + ' MB. Please choose again.';
        return;
      }
      if (names) names.textContent = list.map(function (f) { return f.name; }).join(', ');
    };
    input.addEventListener('change', show);
    ['dragenter', 'dragover'].forEach(function (ev) { box.addEventListener(ev, function () { box.classList.add('is-drag'); }); });
    ['dragleave', 'drop'].forEach(function (ev) { box.addEventListener(ev, function () { box.classList.remove('is-drag'); }); });
  });

  /* ---------- Star rating ---------- */
  $$('[data-cp-stars]').forEach(function (grp) {
    var radios = $$('input[type=radio]', grp);
    var label = $('.cp-rating-label', grp.parentNode);
    var words = ['', 'Poor', 'Fair', 'Good', 'Very good', 'Excellent'];
    var paint = function () {
      var v = 0;
      radios.forEach(function (r) { if (r.checked) v = parseInt(r.value, 10); });
      radios.forEach(function (r) { r.closest('.cp-star').classList.toggle('is-on', parseInt(r.value, 10) <= v); });
      if (label) label.textContent = v ? v + ' of 5 · ' + words[v] : '';
    };
    radios.forEach(function (r) { r.addEventListener('change', paint); });
    paint();
  });

  /* ---------- Confirm dialog ---------- */
  var dlg = null, pending = null;
  function ensureDialog() {
    if (dlg) return dlg;
    dlg = document.createElement('div');
    dlg.className = 'cp-modal'; dlg.hidden = true; dlg.id = 'cp-confirm';
    dlg.setAttribute('role', 'alertdialog'); dlg.setAttribute('aria-modal', 'true'); dlg.setAttribute('aria-labelledby', 'cp-confirm-title');
    dlg.innerHTML = '<div class="cp-modal-box"><h2 id="cp-confirm-title">Are you sure?</h2><p data-cp-confirm-text></p>' +
      '<div class="cp-actions"><button type="button" class="cp-btn is-primary" data-cp-yes>Yes, continue</button><button type="button" class="cp-btn is-light" data-cp-no>Go back</button></div></div>';
    ($('[data-cp-shell]') || document.body).appendChild(dlg);
    $('[data-cp-no]', dlg).addEventListener('click', closeDialog);
    $('[data-cp-yes]', dlg).addEventListener('click', function () { var p = pending; closeDialog(true); if (p) p(); });
    dlg.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDialog(); });
    return dlg;
  }
  var lastFocus = null;
  function closeDialog(skipFocus) { if (!dlg) return; dlg.hidden = true; pending = null; if (lastFocus && skipFocus !== true) lastFocus.focus(); }
  function openDialog(text, ok) {
    ensureDialog(); lastFocus = document.activeElement; pending = ok;
    $('[data-cp-confirm-text]', dlg).textContent = text; dlg.hidden = false; $('[data-cp-no]', dlg).focus();
  }
  document.addEventListener('submit', function (e) {
    var f = e.target, msg = f.getAttribute && f.getAttribute('data-cp-confirm');
    var btn = e.submitter && e.submitter.getAttribute('data-cp-confirm') ? e.submitter : null;
    msg = btn ? btn.getAttribute('data-cp-confirm') : msg;
    if (!msg || f.__cpOk) return;
    e.preventDefault();
    openDialog(msg, function () { f.__cpOk = true; if (btn && f.requestSubmit) f.requestSubmit(btn); else f.submit(); });
  });

  /* ---------- Submit once ---------- */
  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    $$('button[type=submit]:not([data-cp-keep]), input[type=submit]', e.target).forEach(function (b) {
      setTimeout(function () { b.disabled = true; b.setAttribute('aria-disabled', 'true'); }, 0);
    });
  });

  /* ---------- Request form: step indicator + client-side required check ---------- */
  var rf = $('[data-cp-form-steps]');
  if (rf) {
    var steps = $$('.cp-step');
    var groups = [$$('[data-step="1"]', rf), $$('[data-step="2"]', rf), $$('[data-step="3"]', rf)];
    var filled = function (els) { return els.every(function (el) { return el.type === 'checkbox' ? el.checked : (el.value || '').trim() !== ''; }); };
    var refresh = function () {
      var cur = 0;
      groups.forEach(function (g, i) { if (g.length && filled(g)) cur = i + 1; });
      steps.forEach(function (s, i) { s.classList.toggle('is-done', i < cur); s.classList.toggle('is-current', i === Math.min(cur, steps.length - 1)); });
    };
    rf.addEventListener('input', refresh); rf.addEventListener('change', refresh); refresh();
    rf.addEventListener('submit', function (e) {
      var bad = $$('[required]', rf).filter(function (el) { return !el.disabled && (el.type === 'checkbox' ? !el.checked : !(el.value || '').trim()); });
      $$('[aria-invalid]', rf).forEach(function (el) { el.removeAttribute('aria-invalid'); });
      if (bad.length) { e.preventDefault(); bad.forEach(function (el) { el.setAttribute('aria-invalid', 'true'); }); bad[0].focus(); }
    });
  }

  /* ---------- Tabs (client-side filter) ---------- */
  $$('[data-cp-tabs]').forEach(function (tabs) {
    var scope = document.getElementById(tabs.getAttribute('data-cp-tabs')) || document;
    var btns = $$('[data-filter]', tabs);
    var apply = function (key) {
      btns.forEach(function (b) { var on = b.getAttribute('data-filter') === key; b.setAttribute('aria-selected', on ? 'true' : 'false'); });
      var any = false;
      $$('[data-cp-tab]', scope).forEach(function (row) {
        var ok = key === 'all' || (row.getAttribute('data-cp-tab') || '').split(' ').indexOf(key) > -1;
        row.hidden = !ok; if (ok) any = true;
      });
      var empty = $('[data-cp-tab-empty]', scope); if (empty) empty.hidden = any;
    };
    btns.forEach(function (b) { b.addEventListener('click', function () { apply(b.getAttribute('data-filter')); }); });
  });

  /* ---------- Print / copy ---------- */
  $$('[data-cp-print]').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
  $$('[data-cp-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var t = b.getAttribute('data-cp-copy'), old = b.textContent;
      (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = old; }, 1500); }, function () {});
    });
  });

  /* ---------- Service search (dashboard + public results) ----------
     <form data-cp-search data-endpoint="/services/search/" data-results="#id">
       inputs named q, category, region.  Without data-results the form just navigates to its action (GET).
     JSON from the endpoint: {"results":[{id,name,category,description?,url?}]}                          */
  $$('[data-cp-search]').forEach(function (form) {
    var target = form.getAttribute('data-results') && $(form.getAttribute('data-results'));
    var endpoint = form.getAttribute('data-endpoint');
    if (!target || !endpoint) return;
    var timer, seq = 0;
    var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
    var run = function () {
      var mine = ++seq, p = new URLSearchParams(new FormData(form));
      target.hidden = false; target.innerHTML = '<p class="cp-small">Searching…</p>';
      fetch(endpoint + '?' + p.toString(), { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) {
          if (mine !== seq) return;
          var list = (d && d.results) || [];
          target.innerHTML = list.length ? list.map(function (x) {
            return '<a class="cp-shortcut" href="' + esc(x.url || '#') + '"><span><b>' + esc(x.name) + '</b><br><span class="cp-small">' + esc(x.category || '') + '</span></span></a>';
          }).join('') : '<p class="cp-small">No services match. Try another word or area.</p>';
        })
        .catch(function () { if (mine === seq) target.innerHTML = '<p class="cp-small">Search is unavailable right now. Please try again.</p>'; });
    };
    form.addEventListener('submit', function (e) { e.preventDefault(); run(); });
    $$('select', form).forEach(function (s) { s.addEventListener('change', run); });
    var q = $('input[name=q]', form);
    if (q) q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 300); });
  });
})();
