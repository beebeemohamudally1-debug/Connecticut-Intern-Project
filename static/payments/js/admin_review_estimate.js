/* Labour Quotations - Review Labour Estimate.
   Opens the three pop-ups, checks that a reason was written for Revision and
   Reject, then shows the result on the page (demo only: nothing is saved until
   the backend is connected; the real page reloads with the new status instead). */
(function () {
  var pill = document.querySelector('[data-pill]');
  var next = document.querySelector('[data-next]');

  var results = {
    approve: {
      pill: 'Needs quote', cls: 'is-quote',
      title: 'Labour cost approved',
      text: 'MUR {amount} from {handyman} is approved. Next, prepare the customer quotation.',
      button: 'Prepare Quotation', url: 'prepare'
    },
    revision: {
      pill: 'Awaiting handyman', cls: 'is-handyman',
      title: 'Revision requested',
      text: '{handyman} has been asked to change the estimate. You can review it again once they send a new one.',
      button: 'Back to Service Quotations', url: 'back'
    },
    reject: {
      pill: 'Declined', cls: 'is-declined',
      title: 'Labour cost rejected',
      text: 'The estimate is closed and {handyman} can see your reason.',
      button: 'Back to Service Quotations', url: 'back'
    }
  };

  function show(kind) {
    var r = results[kind];
    var d = next.dataset;
    pill.textContent = r.pill;
    pill.className = 'b re-pill ' + r.cls;

    var box = document.createElement('div');
    var h = document.createElement('h2');
    h.textContent = r.title;
    var p = document.createElement('p');
    p.className = 'mut';
    p.textContent = r.text.replace('{amount}', d.amount).replace('{handyman}', d.handyman);
    var note = document.createElement('p');
    note.className = 're-demo-note';
    note.textContent = 'Demo only: nothing is saved until the backend is connected.';
    box.appendChild(h); box.appendChild(p); box.appendChild(note);

    var link = document.createElement('a');
    link.className = 'btn o';
    link.textContent = r.button;
    link.href = r.url === 'prepare' ? d.prepareUrl : d.backUrl;
    var wrap = document.createElement('div');
    wrap.className = 're-actions';
    wrap.appendChild(link);

    next.innerHTML = '';
    next.appendChild(box);
    next.appendChild(wrap);
  }

  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var modal = document.getElementById('modal-' + btn.dataset.open);
      if (!modal) return;
      modal.showModal();
      var note = modal.querySelector('[data-note]');
      if (note) note.focus();
    });
  });

  document.querySelectorAll('.re-modal').forEach(function (modal) {
    modal.querySelectorAll('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () { modal.close(); });
    });
    // Clicking the dark area outside the pop-up also closes it
    modal.addEventListener('click', function (e) { if (e.target === modal) modal.close(); });

    var form = modal.querySelector('form');
    var note = modal.querySelector('[data-note]');
    var error = modal.querySelector('[data-error]');

    if (note) {
      note.addEventListener('input', function () {
        error.hidden = true;
        note.removeAttribute('aria-invalid');
      });
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (note && !note.value.trim()) {
        error.hidden = false;
        note.setAttribute('aria-invalid', 'true');
        note.focus();
        return;
      }
      modal.close();
      if (note) note.value = '';
      show(form.dataset.form);
    });
  });
})();