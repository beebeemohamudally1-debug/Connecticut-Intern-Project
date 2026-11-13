/* Complaints - Case Overview, Private conversations, Resolve case.
   Keeps the thread scrolled to the newest message, and shows a short message
   instead of submitting while a form is not connected yet. */
(function () {
  var msgs = document.querySelector('[data-msgs]');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;

  Array.prototype.forEach.call(document.querySelectorAll('form[data-demo]'), function (form) {
    form.addEventListener('submit', function (e) {
      var action = form.getAttribute('action');
      if (action && action !== '#') return;       // real backend: submit normally
      e.preventDefault();
      var note = form.querySelector('.cc-demo');
      if (!note) {
        note = document.createElement('p');
        note.className = 'cc-notice cc-demo';
        note.setAttribute('role', 'status');
        form.appendChild(note);
      }
      note.textContent = form.dataset.demo;
    });
  });
})();