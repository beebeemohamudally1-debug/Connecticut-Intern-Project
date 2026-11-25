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
        rejectForm.action = btn.dataset.receipt;
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
