/* Service Quotations - Create Service Quotation (admin).
   Also used by Edit / Revise (quotation_edit.html), which has no Send button.
   Works out the margin and total as the admin types, checks the form,
   opens the preview and asks before sending. */
(function () {
  var form = document.querySelector('[data-form]');
  if (!form) return;

  var hasEstimate = form.dataset.labour !== undefined;
  var labour = parseFloat(form.dataset.labour) || 0;
  var percent = form.querySelector('[data-percent]');
  var percentError = form.querySelector('[data-percent-error]');
  var marginOut = form.querySelector('[data-margin]');
  var totalOut = form.querySelector('[data-total]');
  var totalInput = form.querySelector('[data-total-input]');
  var totalError = form.querySelector('[data-total-error]');
  var work = form.querySelector('[data-work]');
  var workError = form.querySelector('[data-work-error]');

  function money(n) {
    return 'MUR ' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function pctValue() {
    var v = parseFloat(percent.value);
    return (isNaN(v) || v < 0 || v > 100) ? null : v;
  }
  function total() {
    var v = parseFloat(totalInput.value);
    return isNaN(v) ? null : v;
  }

  function recalc() {
    if (!hasEstimate) return;
    var p = pctValue();
    percentError.hidden = p !== null;
    percent.setAttribute('aria-invalid', p === null ? 'true' : 'false');
    if (p === null) { marginOut.textContent = '-'; totalOut.textContent = '-'; totalInput.value = ''; return; }
    var margin = Math.round(labour * p) / 100;
    marginOut.textContent = money(margin);
    totalOut.textContent = money(labour + margin);
    totalInput.value = (labour + margin).toFixed(2);
  }

  function check() {
    var ok = true;
    if (!work.value.trim()) {
      workError.hidden = false;
      work.setAttribute('aria-invalid', 'true');
      if (work.type !== 'hidden') work.focus();
      ok = false;
    }
    if (hasEstimate && pctValue() === null) { percent.focus(); ok = false; }
    if (total() === null || total() <= 0) {
      totalError.hidden = false;
      if (!hasEstimate) { totalInput.setAttribute('aria-invalid', 'true'); if (ok) totalInput.focus(); }
      ok = false;
    }
    return ok;
  }

  // After a failed save, start from the margin of the total that was sent
  if (hasEstimate && totalInput.hasAttribute('data-bound') && total() && labour) {
    percent.value = Math.round((total() / labour - 1) * 1000) / 10;
  }
  if (percent) percent.addEventListener('input', function () { totalError.hidden = true; recalc(); });
  work.addEventListener('input', function () { workError.hidden = true; work.removeAttribute('aria-invalid'); });
  if (!hasEstimate) totalInput.addEventListener('input', function () { totalError.hidden = true; totalInput.removeAttribute('aria-invalid'); });

  // Save Draft: check first
  form.querySelector('[data-submit]').addEventListener('click', function (e) { if (!check()) e.preventDefault(); });

  function wire(modal) {
    modal.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { modal.close(); }); });
    modal.addEventListener('click', function (e) { if (e.target === modal) modal.close(); });
    return modal;
  }

  // Preview
  var preview = wire(document.getElementById('modal-preview'));
  form.querySelector('[data-open="preview"]').addEventListener('click', function () {
    if (!check()) return;
    preview.querySelector('[data-pv-work]').textContent = work.value.trim();
    preview.querySelector('[data-pv-total]').textContent = money(total());
    preview.showModal();
  });

  // Send to Customer (Create only): confirm first, the pop-up's button submits the form
  var sendModal = document.getElementById('modal-send');
  var sendBtn = form.querySelector('[data-send]');
  if (sendModal && sendBtn) {
  var send = wire(sendModal);
  sendBtn.addEventListener('click', function () {
    if (!check()) return;
    send.querySelector('[data-sd-total]').textContent = money(total());
    send.showModal();
  });
  }

  recalc();
})();