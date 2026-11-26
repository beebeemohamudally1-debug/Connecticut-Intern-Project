/* Payment Status (admin): pop-ups, the receipt Reject form and the demo form.
   [data-open] opens a <dialog>, [data-close] closes it. Reject uses the receipt's own URL
   (data-receipt) and needs a reason. Forms with data-demo save nothing yet. */
(function () {
  var rejectForm = document.querySelector('[data-reject-form]');

  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = document.getElementById(btn.dataset.open);
      if (!d) return;
      if (btn.dataset.receipt && rejectForm) {
        rejectForm.setAttribute('action', btn.dataset.receipt);
        rejectForm.reset();
      }
      d.showModal();
    });
  });
  document.querySelectorAll('dialog').forEach(function (d) {
    d.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });

  var msg = document.querySelector('[data-demo-msg]');
  document.querySelectorAll('form[data-demo]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var d = form.closest('dialog');
      if (d) d.close();
      if (msg) { msg.firstElementChild.textContent = form.getAttribute('data-demo'); msg.hidden = false; }
    });
  });
})();

/* Approve / Reject a receipt: sent in the background, then this page reloads, so the admin stays on
   Payment Status (the receipt view itself goes to Material Quotations, and has no "next" yet) and sees
   the result here. Locked after the first click, so a double click cannot send it twice. */
(function () {
  document.querySelectorAll('form.ps-inline, form[data-reject-form]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (form.dataset.sent) return;
      form.dataset.sent = '1';
      var btn = e.submitter;
      var data = new FormData(form);
      if (btn && btn.name) data.append(btn.name, btn.value);
      form.querySelectorAll('button').forEach(function (b) { if (b.type !== 'button') b.disabled = true; });
      if (btn) btn.textContent = form.hasAttribute('data-reject-form') ? 'Rejecting…' : 'Approving…';
      // redirect: 'manual' keeps the saved message ("Receipt approved.") for this page instead of the other one
      // getAttribute: form.action would be the button named "action", not the address
      fetch(form.getAttribute('action'), { method: 'POST', body: data, credentials: 'same-origin', redirect: 'manual' })
        .then(function () { location.reload(); })
        .catch(function () { HTMLFormElement.prototype.submit.call(form); });
    });
  });
})();
