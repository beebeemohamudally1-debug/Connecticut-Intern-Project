// Service provider registration (S10 details, S10b documents). Presentation behaviour only:
// the server stays the source of truth for every rule (types, sizes, required fields, consent).
// Hooks are data-pv-* attributes. Without JavaScript the multiselects show as plain checkbox lists
// and the upload fields as normal file inputs, so the form still posts.
document.addEventListener('DOMContentLoaded', () => {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = id => {
    const s = document.createElementNS(NS, 'svg'), u = document.createElementNS(NS, 'use');
    s.setAttribute('class', 'au-ic'); s.setAttribute('aria-hidden', 'true'); u.setAttribute('href', '#' + id); s.appendChild(u);
    return s;
  };
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  // Writes (or clears) a field's error line, same markup the server renders
  const showError = (box, text) => { box.replaceChildren(); if (text) box.append(svg('au-i-alert'), document.createTextNode(text)); };

  // ---------- S10: multiselect with chips ----------
  document.querySelectorAll('[data-pv-ms]').forEach(ms => {
    const input = ms.querySelector('[data-pv-ms-input]'), chips = ms.querySelector('[data-pv-chips]');
    const holder = ms.querySelector('[data-pv-placeholder]'), toggle = ms.querySelector('.pv-ms-toggle');
    const panel = ms.querySelector('[data-pv-panel]'), live = ms.querySelector('[data-pv-live]'), err = ms.querySelector('.rg-error');
    const boxes = [...panel.querySelectorAll('input[type=checkbox]')];
    ms.classList.add('is-js');

    const setOpen = (open, focusToggle) => {
      panel.hidden = !open; toggle.setAttribute('aria-expanded', String(open)); ms.classList.toggle('is-open', open);
      if (!open && focusToggle) toggle.focus();
    };
    const render = announce => {
      const chosen = boxes.filter(b => b.checked);
      chips.replaceChildren();
      chosen.forEach(b => {
        const text = b.closest('label').querySelector('.pv-opt-text').textContent;
        const chip = el('span', 'pv-chip', text), x = el('button', 'pv-chip-x');
        x.type = 'button'; x.setAttribute('aria-label', 'Remove ' + text); x.appendChild(svg('au-i-x'));
        x.addEventListener('click', e => { e.stopPropagation(); b.checked = false; render(true); toggle.focus(); });
        chip.appendChild(x); chips.appendChild(chip);
      });
      holder.hidden = chosen.length > 0;
      if (chosen.length) { showError(err, ''); input.classList.remove('is-bad'); toggle.removeAttribute('aria-invalid'); }
      if (announce) {
        const n = chosen.length;
        live.textContent = n + ' ' + (n === 1 ? ms.dataset.noun : ms.dataset.nounPlural) + ' selected';
      }
    };

    boxes.forEach(b => b.addEventListener('change', () => render(true)));
    input.addEventListener('click', e => { if (!e.target.closest('.pv-chip-x')) setOpen(panel.hidden); });
    toggle.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); (boxes.find(b => b.checked) || boxes[0]).focus(); }
    });
    panel.addEventListener('keydown', e => {
      const i = boxes.indexOf(document.activeElement);
      if (e.key === 'ArrowDown' && i < boxes.length - 1) { e.preventDefault(); boxes[i + 1].focus(); }
      else if (e.key === 'ArrowUp' && i > 0) { e.preventDefault(); boxes[i - 1].focus(); }
      else if (e.key === 'ArrowUp' && i === 0) { e.preventDefault(); setOpen(false, true); }
      else if (e.key === 'Home') { e.preventDefault(); boxes[0].focus(); }
      else if (e.key === 'End') { e.preventDefault(); boxes[boxes.length - 1].focus(); }
    });
    ms.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) { e.stopPropagation(); setOpen(false, true); } });
    ms.addEventListener('focusout', e => { if (e.relatedTarget && !ms.contains(e.relatedTarget)) setOpen(false); });
    document.addEventListener('click', e => { if (!ms.contains(e.target)) setOpen(false); });

    render(false);
    setOpen(ms.classList.contains('is-open-demo'));
    ms.classList.remove('is-open-demo');
  });

  // ---------- S10b: documents ----------
  const MB = 1024 * 1024;
  const sizeLabel = b => b >= MB ? (b / MB).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB';
  const typeLabel = t => t === 'image/png' ? 'PNG' : t === 'image/jpeg' ? 'JPEG' : t;

  document.querySelectorAll('form[data-pv-docs]').forEach(form => {
    const rules = {
      types: (form.dataset.types || 'image/jpeg,image/png').split(','),
      max: (parseInt(form.dataset.maxMb, 10) || 5) * MB,
      typeMsg: form.dataset.msgType || 'Only JPEG or PNG files are accepted.',
      sizeMsg: form.dataset.msgSize || 'Each file must be 5 MB or smaller.',
    };
    let openPreview = null; // only one preview at a time: { row, panel, button }
    const closePreview = back => {
      if (!openPreview) return;
      const { panel, button } = openPreview;
      panel.remove(); button.setAttribute('aria-expanded', 'false'); openPreview = null;
      if (back) button.focus();
    };

    const initField = root => {
      const name = root.dataset.field, multiple = root.dataset.multiple === '1';
      const input = root.querySelector('input[type=file]'), list = root.querySelector('[data-pv-files]');
      const drop = root.querySelector('[data-pv-drop]'), pick = root.querySelector('[data-pv-pick]');
      const status = root.querySelector('[data-pv-status]'), err = root.querySelector('.rg-error');
      const rows = () => [...list.querySelectorAll('.pv-file')];
      root.classList.add('is-js');

      const changed = () => {
        const n = rows().length;
        status.textContent = n === 0 ? 'No files uploaded' : n === 1 ? '1 file uploaded' : n + ' files uploaded';
        pick.querySelector('.au-label').textContent = n > 0 ? pick.dataset.more : pick.dataset.first;
        drop.hidden = !multiple && n > 0;
        form.dispatchEvent(new CustomEvent('pv:change'));
      };
      // Put every new file (in on-screen order) back into the real file input, so the normal POST carries them
      const sync = () => {
        const dt = new DataTransfer();
        rows().forEach(r => { if (r._info.file) dt.items.add(r._info.file); });
        input.files = dt.files;
      };
      const setBad = text => {
        showError(err, text);
        drop.classList.toggle('is-bad', !!text);
        if (text) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
      };

      const makeRow = info => {
        const li = el('li', 'pv-file'); li._info = info;
        const thumb = el('span', 'pv-thumb');
        if (info.url) { const img = document.createElement('img'); img.src = info.url; img.alt = ''; thumb.appendChild(img); }
        else thumb.appendChild(svg('pv-i-file'));
        const main = el('div', 'pv-file-main');
        const actions = el('div', 'pv-file-actions');
        const act = (key, label, cls) => {
          const b = el('button', 'pv-act' + (cls ? ' ' + cls : ''), label);
          b.type = 'button'; b.dataset.act = key; b.setAttribute('aria-label', label + ' ' + info.name); actions.appendChild(b);
          return b;
        };
        const bPreview = act('preview', 'Preview'); bPreview.setAttribute('aria-expanded', 'false');
        const bReplace = act('replace', 'Replace'), bRemove = act('remove', 'Remove', 'is-danger');
        main.append(el('span', 'pv-file-name', info.name), el('span', 'pv-file-meta', info.type + ' · ' + info.size), actions);
        li.append(thumb, main);
        if (info.token) { // a file the server already holds: tell it to keep it unless the user removes it
          const keep = document.createElement('input'); keep.type = 'hidden'; keep.name = 'keep_' + name; keep.value = info.token; li.appendChild(keep);
        }
        bPreview.addEventListener('click', () => showPreview(li, bPreview));
        bReplace.addEventListener('click', () => {
          const t = document.createElement('input'); t.type = 'file'; t.accept = input.accept;
          t.addEventListener('change', () => { if (t.files.length) addFiles(t.files, li); });
          t.click();
        });
        bRemove.addEventListener('click', () => removeRow(li, true));
        return li;
      };

      const dispose = li => { if (li._info.objectUrl) URL.revokeObjectURL(li._info.objectUrl); };
      const removeRow = (li, moveFocus) => {
        if (openPreview && openPreview.row === li) closePreview(false);
        const next = li.nextElementSibling && li.nextElementSibling.classList.contains('pv-file') ? li.nextElementSibling : li.previousElementSibling;
        dispose(li); li.remove(); sync(); changed();
        if (moveFocus) {
          const target = next && next.querySelector('[data-act=remove]');
          (target || (drop.hidden ? null : pick) || input).focus();
        }
      };

      const addFiles = (fileList, replacing) => {
        const problems = [], good = [];
        [...fileList].forEach(f => {
          if (!rules.types.includes(f.type)) problems.push(f.name + ': ' + rules.typeMsg);
          else if (f.size > rules.max) problems.push(f.name + ': ' + rules.sizeMsg);
          else good.push(f);
        });
        const dup = f => rows().some(r => r._info.file && r._info.file.name === f.name && r._info.file.size === f.size);
        let accepted = good.filter(f => !dup(f) || (replacing && replacing._info.file === f));
        if (!multiple) accepted = accepted.slice(0, 1);
        setBad(problems.join(' '));
        accepted.forEach((f, i) => {
          const objectUrl = URL.createObjectURL(f);
          const li = makeRow({ name: f.name, type: typeLabel(f.type), size: sizeLabel(f.size), url: objectUrl, objectUrl, file: f });
          if (replacing && i === 0) { if (openPreview && openPreview.row === replacing) closePreview(false); dispose(replacing); replacing.replaceWith(li); }
          else if (!multiple) { rows().forEach(r => { dispose(r); r.remove(); }); list.appendChild(li); }
          else list.appendChild(li);
        });
        sync(); changed();
        if (accepted.length && !problems.length) setBad('');
      };

      const showPreview = (row, button) => {
        const wasOpen = openPreview && openPreview.row === row;
        closePreview(false);
        if (wasOpen) return;
        const info = row._info, panel = el('li', 'pv-preview');
        panel.setAttribute('role', 'group'); panel.setAttribute('aria-label', 'Preview of ' + info.name);
        const head = el('div', 'pv-preview-head'), close = el('button', 'pv-act', 'Close');
        close.type = 'button'; close.setAttribute('aria-label', 'Close preview of ' + info.name);
        close.addEventListener('click', () => closePreview(true));
        head.append(el('strong', '', 'Preview'), close);
        const body = el('div', 'pv-preview-img');
        if (info.url) { const img = document.createElement('img'); img.src = info.url; img.alt = 'Preview of ' + info.name; body.appendChild(img); }
        else { body.appendChild(svg('pv-i-file')); }
        panel.append(head, body, el('p', 'pv-preview-cap', info.name + ' · ' + info.type + ' · ' + info.size));
        row.after(panel);
        button.setAttribute('aria-expanded', 'true');
        openPreview = { row, panel, button };
        return close;
      };

      // Rows the server already holds ("seeds") become real rows
      list.querySelectorAll('[data-pv-seed]').forEach(seed => {
        const d = seed.dataset;
        seed.replaceWith(makeRow({ name: d.name, type: d.type, size: d.size, url: d.url || '', token: d.token }));
      });

      pick.addEventListener('click', () => input.click());
      input.addEventListener('change', () => { if (input.files.length) addFiles(input.files); else sync(); });
      ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('is-over'); }));
      ['dragleave', 'dragend'].forEach(ev => drop.addEventListener(ev, () => drop.classList.remove('is-over')));
      drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('is-over'); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
      root.addEventListener('keydown', e => { if (e.key === 'Escape' && openPreview) { e.stopPropagation(); closePreview(true); } });
      changed();
      return { name, count: () => rows().length, previewFirst: () => { const r = rows()[0]; if (r) showPreview(r, r.querySelector('[data-act=preview]')); } };
    };

    const fields = [...form.querySelectorAll('[data-pv-upload]')].map(initField);
    const count = n => (fields.find(f => f.name === n) || { count: () => 0 }).count();

    // The Submit button stays disabled until both documents are in and both consents are ticked
    const gate = form.querySelector('[data-pv-gate]');
    const terms = form.querySelector('input[name=terms]'), privacy = form.querySelector('input[name=privacy]');
    const evaluate = () => { if (gate) gate.disabled = !(count('id_photo') > 0 && count('certificates') > 0 && terms.checked && privacy.checked); };
    [terms, privacy].forEach(box => box.addEventListener('change', () => {
      if (box.checked) { const e = document.getElementById(box.name + '-error'); if (e) showError(e, ''); box.removeAttribute('aria-invalid'); }
      evaluate();
    }));
    form.addEventListener('pv:change', evaluate);
    evaluate();

    if (form.dataset.autoPreview) { const f = fields.find(x => x.name === form.dataset.autoPreview); if (f) f.previewFirst(); }
  });
});
