/* ==========================================================
   HandyConnect - Admin Profile page
   - Edit: swaps the text for input boxes (Full Name, Email)
   - Cancel (or Escape): puts the original values back
   - Save: checks the fields first (red * and red error text appear
     only while editing). For now it then only updates the page and
     shows a message, because nothing is saved yet (frontend demo).
   ========================================================== */
(function () {
  'use strict';

  var form = document.querySelector('[data-profile-form]');
  if (!form) { return; }

  var editButton = form.querySelector('[data-edit-toggle]');
  var cancelButton = form.querySelector('[data-edit-cancel]');
  var actions = form.querySelector('[data-edit-actions]');
  var inputs = Array.prototype.slice.call(form.querySelectorAll('[data-edit]'));
  var editOnly = Array.prototype.slice.call(form.querySelectorAll('[data-edit-only]'));
  var toast = document.querySelector('[data-toast]');
  var toastTimer;
  var editing = false;

  /* Error text under an input */
  function errorFor(input) {
    return input.parentNode.querySelector('[data-error]');
  }

  function clearError(input) {
    var error = errorFor(input);
    input.classList.remove('invalid');
    input.removeAttribute('aria-invalid');
    error.textContent = '';
    error.hidden = true;
  }

  function showError(input, text) {
    var error = errorFor(input);
    input.classList.add('invalid');
    input.setAttribute('aria-invalid', 'true');
    error.textContent = text;
    error.hidden = false;
  }

  /* Returns the first input with a problem, or null when all is fine */
  function validate() {
    var firstBad = null;
    inputs.forEach(function (input) {
      var value = input.value.trim();
      clearError(input);
      var message = '';
      if (!value) {
        message = input.type === 'email' ? 'Enter your email address.' : 'Enter your full name.';
      } else if (input.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        message = 'Enter a valid email address.';
      }
      if (message) {
        showError(input, message);
        if (!firstBad) { firstBad = input; }
      }
    });
    return firstBad;
  }

  /* Text shown next to each input (the [data-view] in the same row) */
  function viewFor(input) {
    return input.parentNode.querySelector('[data-view]');
  }

  function setEditing(on) {
    editing = on;
    editButton.hidden = on;
    actions.hidden = !on;
    inputs.forEach(function (input) {
      input.hidden = !on;
      viewFor(input).hidden = on;
      if (!on) { clearError(input); }
    });
    editOnly.forEach(function (item) { item.hidden = !on; });
  }

  function showMessage(text) {
    if (!toast) { return; }
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.hidden = true; }, 3500);
  }

  function startEdit() {
    /* Remember the values so Cancel can restore them */
    inputs.forEach(function (input) { input.defaultValue = input.value; });
    setEditing(true);
    inputs[0].focus();
  }

  function cancelEdit() {
    inputs.forEach(function (input) { input.value = input.defaultValue; });
    setEditing(false);
    editButton.focus();
  }

  inputs.forEach(function (input) {
    input.addEventListener('input', function () { clearError(input); });
  });

  editButton.addEventListener('click', startEdit);
  cancelButton.addEventListener('click', cancelEdit);

  form.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && editing) { cancelEdit(); }
  });

  form.addEventListener('submit', function (event) {
    var firstBad = validate();
    if (firstBad) {
      event.preventDefault();
      firstBad.focus();
      return;
    }

    /* BACKEND: once the profile update view exists, remove data-demo from the
       form in the HTML. This block is then skipped and the form posts normally. */
    if (!form.hasAttribute('data-demo')) { return; }
    event.preventDefault();

    inputs.forEach(function (input) {
      input.value = input.value.trim();
      viewFor(input).textContent = input.value;
    });
    setEditing(false);
    editButton.focus();
    showMessage(form.getAttribute('data-demo'));
  });
})();