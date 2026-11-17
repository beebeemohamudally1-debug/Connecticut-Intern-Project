/* Service Quotations - Service Quotation Details (admin).
   Works out the admin margin (total minus the handyman estimate) and opens the pop-ups. */
(function () {
  var box = document.querySelector('[data-amounts]');
  if (box && box.dataset.labour) {
    var total = parseFloat(box.dataset.total), labour = parseFloat(box.dataset.labour);
    var margin = total - labour;
    var out = box.querySelector('[data-margin]'), pct = box.querySelector('[data-pct]');
    if (out && !isNaN(margin)) {
      out.textContent = 'MUR ' + margin.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      if (labour > 0 && pct) pct.textContent = '(' + Math.round(margin / labour * 1000) / 10 + '%)';
    }
  }

  document.querySelectorAll('[data-open]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = document.getElementById(btn.dataset.open);
      if (d) d.showModal();
    });
  });
  document.querySelectorAll('.qd-modal').forEach(function (d) {
    d.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
  });

  // Customer response prompt: opens by itself the first time this answer is viewed (this browser only)
  var resp = document.getElementById('modal-response');
  if (resp) {
    var key = resp.dataset.responseKey, seen = false;
    try { seen = localStorage.getItem(key) === '1'; } catch (e) { seen = true; }
    function markSeen() { try { localStorage.setItem(key, '1'); } catch (e) {} }
    resp.querySelectorAll('[data-seen]').forEach(function (b) { b.addEventListener('click', markSeen); });
    if (resp.hasAttribute('data-auto') && !seen) resp.showModal();
  }
})();