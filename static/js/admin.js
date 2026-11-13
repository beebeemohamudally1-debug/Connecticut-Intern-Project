/* HandyConnect - Admin portal scripts (loaded on every Admin page)
   Sections (more are added as pages need them):
     1. Sidebar drawer on phones
     2. Admin name drop-down menu (View Profile, Logout)
*/
(function () {
  'use strict';

  /* ---------- 1. Sidebar drawer on phones ----------
     Below 768px the sidebar is a drawer. Opening it adds the class
     "nav-open" to <body>, and the CSS slides the drawer in and dims the page.
     It closes with the X button, a tap on the dark area, a tap on a link, or
     the Escape key. */
  var navButton = document.querySelector('[data-nav-toggle]');
  var closeButtons = document.querySelectorAll('[data-nav-close]');
  var sidebar = document.getElementById('admin-sidebar');

  function setNav(open) {
    document.body.classList.toggle('nav-open', open);
    if (navButton) { navButton.setAttribute('aria-expanded', String(open)); }
  }

  if (navButton && sidebar) {
    navButton.addEventListener('click', function () {
      setNav(true);
      // Move the keyboard focus into the drawer (the X button is the first thing in it).
      // Wait a moment: a drawer that is still hidden cannot take focus.
      setTimeout(function () { sidebar.querySelector('.sb-close').focus(); }, 50);
    });

    closeButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        setNav(false);
        navButton.focus();
      });
    });

    // Tapping a link closes the drawer (on the next page it starts closed anyway)
    sidebar.querySelectorAll('nav a').forEach(function (link) {
      link.addEventListener('click', function () { setNav(false); });
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && document.body.classList.contains('nav-open')) {
        setNav(false);
        navButton.focus();
      }
    });

    // Turning a tablet sideways (or widening the window) leaves no stuck drawer
    window.addEventListener('resize', function () {
      if (window.innerWidth >= 768) { setNav(false); }
    });
  }

  /* ---------- 2. Admin name drop-down ----------
     The button and the menu are in templates/base_admin.html:
       <button data-user-menu-btn> ... </button>
       <div data-user-menu hidden> ... </div>
     Opening and closing means adding or removing the "hidden" attribute. */
  var menuButton = document.querySelector('[data-user-menu-btn]');
  var menu = document.querySelector('[data-user-menu]');

  function setMenu(open) {
    menu.hidden = !open;
    menuButton.setAttribute('aria-expanded', String(open));
  }

  if (menuButton && menu) {
    // Click the name: open if closed, close if open
    menuButton.addEventListener('click', function (event) {
      event.stopPropagation();   // so the "click anywhere else" rule below does not close it at once
      setMenu(menu.hidden);
    });

    // Click anywhere outside the menu: close it
    document.addEventListener('click', function (event) {
      if (!menu.hidden && !menu.contains(event.target)) {
        setMenu(false);
      }
    });

    // Escape key: close it and give focus back to the name button
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !menu.hidden) {
        setMenu(false);
        menuButton.focus();
      }
    });
  }
})();