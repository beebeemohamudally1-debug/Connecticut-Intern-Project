/* ==========================================================
   HandyConnect - Administrator Dashboard
   1. Tabs (Recent Activities / Pending Tasks): one panel at a
      time. Works with the mouse and with the keyboard (Left and
      Right arrows, Home, End).
   2. Filter buttons inside Pending Tasks: All shows every task,
      the others show only that category.
   ========================================================== */
(function () {
  'use strict';

  function setup(tablist) {
    var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (tab) {
      return document.getElementById(tab.getAttribute('aria-controls'));
    });

    function select(index, moveFocus) {
      tabs.forEach(function (tab, i) {
        var on = i === index;
        tab.setAttribute('aria-selected', on ? 'true' : 'false');
        tab.tabIndex = on ? 0 : -1;
        panels[i].hidden = !on;
      });
      if (moveFocus) { tabs[index].focus(); }
    }

    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { select(i, false); });

      tab.addEventListener('keydown', function (event) {
        var last = tabs.length - 1;
        var next = null;
        if (event.key === 'ArrowRight') { next = i === last ? 0 : i + 1; }
        if (event.key === 'ArrowLeft') { next = i === 0 ? last : i - 1; }
        if (event.key === 'Home') { next = 0; }
        if (event.key === 'End') { next = last; }
        if (next !== null) {
          event.preventDefault();
          select(next, true);
        }
      });
    });

    /* Start on the first tab */
    select(0, false);
  }

  Array.prototype.forEach.call(document.querySelectorAll('[role="tablist"]'), setup);

  /* ---- Filter buttons ---- */
  var bar = document.querySelector('[data-filters]');
  if (!bar) { return; }

  var buttons = Array.prototype.slice.call(bar.querySelectorAll('[data-filter]'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('[data-task-list] .task'));
  var list = document.querySelector('[data-task-list]');
  var payDetail = document.querySelector('[data-pay-detail]');

  function filter(name) {
    buttons.forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-filter') === name ? 'true' : 'false');
    });

    /* Payments shows its own details (numbers + table) instead of the row */
    var showPay = name === 'payments';
    list.hidden = showPay;
    if (payDetail) { payDetail.hidden = !showPay; }

    rows.forEach(function (row) {
      row.hidden = !(name === 'all' || row.getAttribute('data-cat') === name);
    });
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () { filter(b.getAttribute('data-filter')); });
  });

  filter('all');
})();