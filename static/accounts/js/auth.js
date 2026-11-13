// Presentation behaviour only. The server stays the source of truth for every rule.
// Hooks are data-au-* attributes so this file never touches other pages' markup.
document.addEventListener('DOMContentLoaded', () => {
  // Show / hide password (eye button inside the field)
  document.querySelectorAll('[data-au-toggle]').forEach(btn => btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.auToggle);
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-pressed', String(show));
    btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    btn.querySelector('use').setAttribute('href', show ? '#au-i-eye' : '#au-i-eye-off');
  }));

  // Six-box code input: auto-advance, backspace, paste a full code.
  // Fills the hidden field and enables the [data-au-gate] button once all 6 digits exist.
  document.querySelectorAll('[data-au-otp]').forEach(wrap => {
    const boxes = [...wrap.querySelectorAll('input')];
    const hidden = document.getElementById(wrap.dataset.auOtp);
    const gated = wrap.closest('form').querySelector('[data-au-gate]');
    const sync = () => {
      hidden.value = boxes.map(b => b.value).join('');
      if (gated) gated.disabled = hidden.value.length < 6;
    };
    boxes.forEach((box, i) => {
      box.addEventListener('input', () => {
        box.value = box.value.replace(/\D/g, '');
        sync();
        if (box.value && boxes[i + 1]) boxes[i + 1].focus();
      });
      box.addEventListener('keydown', e => {
        if (e.key === 'Backspace' && !box.value && boxes[i - 1]) boxes[i - 1].focus();
      });
      box.addEventListener('paste', e => {
        e.preventDefault();
        const digits = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6);
        [...digits].forEach((c, j) => { boxes[j].value = c; });
        sync();
        (boxes.find(x => !x.value) || boxes[5]).focus();
      });
    });
    boxes[0].focus();
  });

  // Countdown (mm:ss) from the seconds in data-au-countdown
  document.querySelectorAll('[data-au-countdown]').forEach(el => {
    let s = parseInt(el.dataset.auCountdown, 10) || 0;
    const draw = () => { el.textContent = String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
    draw();
    const id = setInterval(() => { if (s > 0) { s--; draw(); } else { clearInterval(id); } }, 1000);
  });

  // Resend cooldown: disable the button and show the seconds left
  document.querySelectorAll('[data-au-cooldown]').forEach(btn => {
    let s = parseInt(btn.dataset.auCooldown, 10);
    if (!s) return;
    const label = btn.querySelector('.au-label');
    const base = label.textContent;
    btn.disabled = true;
    label.textContent = base + ' (' + s + 's)';
    const id = setInterval(() => {
      s--;
      if (s <= 0) { clearInterval(id); btn.disabled = false; label.textContent = base; }
      else { label.textContent = base + ' (' + s + 's)'; }
    }, 1000);
  });

  // Live password checklist. The "common password" rule is server-only and stays as rendered.
  const tests = { len: p => p.length >= 8, upper: p => /[A-Z]/.test(p), lower: p => /[a-z]/.test(p), digit: p => /\d/.test(p) };
  document.querySelectorAll('[data-au-rules]').forEach(list => {
    const input = document.getElementById(list.dataset.auRules);
    input.addEventListener('input', () => list.querySelectorAll('[data-rule]').forEach(li => {
      const test = tests[li.dataset.rule];
      if (!test) return;
      const ok = test(input.value);
      li.classList.toggle('is-met', ok);
      li.querySelector('.au-mark').textContent = ok ? '✓' : '○';
      li.querySelector('.au-sr').textContent = ok ? ' (met)' : ' (not met)';
    }));
  });

  // Block double submit and show the loading state
  document.querySelectorAll('form[data-au-once]').forEach(form => form.addEventListener('submit', e => {
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (form.dataset.sent) { e.preventDefault(); return; }
    form.dataset.sent = '1';
    if (btn) btn.classList.add('is-loading');
  }));
});
