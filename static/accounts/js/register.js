// Presentation behaviour for the registration pages. The server stays the source of truth for every rule.
document.addEventListener('DOMContentLoaded', () => {
  // S02: Continue stays disabled until an account type is chosen
  document.querySelectorAll('[data-rg-roles]').forEach(group => {
    const btn = group.closest('form').querySelector('[data-rg-gate]');
    const sync = () => { if (btn) btn.disabled = !group.querySelector('input:checked'); };
    group.addEventListener('change', sync);
    sync();
  });

  // S05: the Verify button starts disabled until all six digits are entered (auth.js enables it as you type)
  document.querySelectorAll('button[data-au-gate]').forEach(btn => {
    const code = btn.closest('form').querySelector('#code');
    if (code && code.value.length < 6) btn.disabled = true;
  });

  // Small helpers to write into a field's error line (same markup the server renders)
  const errorBox = id => document.getElementById(id + '-error');
  const setError = (input, text) => {
    const box = errorBox(input.id);
    if (!box) return;
    box.replaceChildren();
    if (text) {
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('class', 'au-ic'); icon.setAttribute('aria-hidden', 'true');
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', '#au-i-alert'); icon.appendChild(use);
      box.append(icon, document.createTextNode(text));
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.removeAttribute('aria-invalid');
    }
  };

  // S06: strength meter (text + bar) and a gentle "passwords do not match" hint when leaving the confirm field
  document.querySelectorAll('[data-rg-strength]').forEach(meter => {
    const input = document.getElementById(meter.dataset.rgStrength);
    const label = meter.querySelector('b');
    input.addEventListener('input', () => {
      const p = input.value;
      const score = [p.length >= 8, /[A-Z]/.test(p), /[a-z]/.test(p), /\d/.test(p)].filter(Boolean).length;
      // empty: Not started | up to 2 rules: Weak | 3 rules: Fair | all 4: Good, or Strong with 12+ characters
      let level = 0, name = 'Not started';
      if (p) {
        if (score <= 2) { level = 1; name = 'Weak'; }
        else if (score === 3) { level = 2; name = 'Fair'; }
        else if (p.length < 12) { level = 3; name = 'Good'; }
        else { level = 4; name = 'Strong'; }
      }
      meter.dataset.level = level;
      label.textContent = name;
    });
  });
  const confirm = document.getElementById('confirm'), pw = document.getElementById('password');
  if (confirm && pw) {
    const MISMATCH = 'Passwords do not match.';
    confirm.addEventListener('blur', () => { if (confirm.value) setError(confirm, confirm.value === pw.value ? '' : MISMATCH); });
    confirm.addEventListener('input', () => { if (confirm.getAttribute('aria-invalid') && confirm.value === pw.value) setError(confirm, ''); });
  }

  // S08: phone accepts digits only
  const phone = document.getElementById('phone');
  if (phone) phone.addEventListener('input', () => { phone.value = phone.value.replace(/\D/g, '').slice(0, 8); });

  // S08: live username check on blur. The server still checks again on submit.
  const user = document.querySelector('[data-rg-check-url]');
  const status = document.getElementById('username-status');
  if (user && status) {
    let seq = 0;
    const show = (ok, text) => {
      status.replaceChildren(); status.classList.toggle('is-ok', ok);
      if (!text) return;
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('class', 'au-ic'); icon.setAttribute('aria-hidden', 'true');
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', ok ? '#au-i-check' : '#au-i-alert'); icon.appendChild(use);
      status.append(icon, document.createTextNode(text));
    };
    user.addEventListener('input', () => { show(false, ''); setError(user, ''); });
    user.addEventListener('blur', async () => {
      const name = user.value.trim();
      if (!/^\w{3,30}$/.test(name)) return; // format errors are shown by the server on submit
      const mine = ++seq;
      try {
        const res = await fetch(user.dataset.rgCheckUrl + '?username=' + encodeURIComponent(name), { headers: { Accept: 'application/json' } });
        if (mine !== seq) return;
        const data = await res.json();
        if (res.ok) show(true, 'Username is available.');
        else if (res.status === 409) { show(false, ''); setError(user, data.message); }
      } catch (e) { /* offline: the server check on submit still applies */ }
    });
  }
});
