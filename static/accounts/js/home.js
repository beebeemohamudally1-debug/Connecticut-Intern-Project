/* HandyConnect visitor landing page.
   1. Sticky nav gets a shadow once scrolled.
   2. Mobile menu toggle.
   3. Service search: the form, "Popular" links, category cards, area chips and "Meet all professionals" all run
      one search against the form's action URL and show the JSON inline in #results.
      No JS = the same links and form just load the search URL as a normal page.

   BACKEND CONTRACT (the existing services:search route already matches it):
     Request   GET <form action>?q=<text>&region=<ServiceArea.name>&category=<ServiceCategory.name>
               Header  Accept: application/json   (empty params are left out)
     Response  200 {"results": [{"id": 1, "name": "Pipe leak repair", "category": "Plumbing",
                                 "description": "optional", "url": "optional link for the result"}]}
               Any non-2xx or invalid JSON shows the error state with a "Try again" button.
     "region" is sent but the current route ignores it; filter on it when ready, nothing here changes.
     Result link: result.url if present, else the form's data-request-href (the registration page). */
(function () {
  "use strict";

  /* ---------- 1. Nav shadow ---------- */
  var nav = document.querySelector(".hm-nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 4); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- 2. Mobile menu ---------- */
  var toggle = document.querySelector("[data-menu-toggle]");
  var menu = document.querySelector("[data-menu]");
  function setMenu(open) {
    if (!toggle || !menu) return;
    toggle.setAttribute("aria-expanded", String(open));
    menu.classList.toggle("is-open", open);
  }
  if (toggle && menu) {
    toggle.addEventListener("click", function () { setMenu(toggle.getAttribute("aria-expanded") !== "true"); });
    menu.addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") { setMenu(false); toggle.focus(); }
    });
  }

  /* Placeholder footer links (href="#") should not jump to the top of the page */
  document.addEventListener("click", function (e) {
    var a = e.target.closest('a[href="#"]');
    if (a) e.preventDefault();
  });

  /* "Find a service" links and buttons: scroll to the search box and focus it */
  var form = document.querySelector("[data-search-form]");
  var qInput = form && form.querySelector("[data-search-q]");
  var regionSelect = form && form.querySelector("[data-search-region]");
  document.addEventListener("click", function (e) {
    var a = e.target.closest("[data-focus-search]");
    if (!a || !qInput) return;
    e.preventDefault();
    setMenu(false);
    form.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    window.setTimeout(function () { qInput.focus({ preventScroll: true }); }, 250);
  });

  /* ---------- 3. Search ---------- */
  var panel = document.querySelector("[data-results]");
  if (!form || !panel || !window.fetch) return;

  var list = panel.querySelector("[data-results-list]");
  var statusEl = panel.querySelector("[data-results-status]");
  var titleEl = panel.querySelector("[data-results-title]");
  var emptyEl = panel.querySelector("[data-results-empty]");
  var errorEl = panel.querySelector("[data-results-error]");
  var lastParams = null;
  var requestId = 0;

  function regionLabel(value) {
    if (!regionSelect) return value;
    for (var i = 0; i < regionSelect.options.length; i++) {
      if (regionSelect.options[i].value === value) return regionSelect.options[i].text;
    }
    return value;
  }

  function buildResult(item) {
    var li = document.createElement("li");
    var card = document.createElement("article");
    card.className = "hm-result";
    if (item.category) {
      var cat = document.createElement("span");
      cat.className = "hm-result-cat";
      cat.textContent = item.category;
      card.appendChild(cat);
    }
    var h = document.createElement("h3");
    h.textContent = item.name || "Service";
    card.appendChild(h);
    if (item.description) {
      var p = document.createElement("p");
      p.textContent = item.description;
      card.appendChild(p);
    }
    var a = document.createElement("a");
    a.href = item.url || form.getAttribute("data-request-href") || "#";
    a.appendChild(document.createTextNode("Request this service "));
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "hm-ic");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#hm-i-arrow-right");
    svg.appendChild(use);
    a.appendChild(svg);
    card.appendChild(a);
    li.appendChild(card);
    return li;
  }

  function describe(params) {
    var bits = [];
    if (params.q) bits.push("“" + params.q + "”");
    if (params.category) bits.push(params.category);
    var s = bits.length ? bits.join(" · ") : "All services";
    if (params.region) s += " in " + regionLabel(params.region);
    return s;
  }

  function show(state) {
    list.hidden = state !== "results";
    emptyEl.hidden = state !== "empty";
    errorEl.hidden = state !== "error";
  }

  function run(params, focusPanel) {
    lastParams = params;
    var id = ++requestId;
    var url = new URL(form.getAttribute("action") || window.location.pathname, window.location.href);
    Object.keys(params).forEach(function (k) { if (params[k]) url.searchParams.set(k, params[k]); });

    panel.hidden = false;
    titleEl.textContent = describe(params);
    statusEl.textContent = "Searching…";
    list.textContent = "";
    show("results");
    form.classList.add("is-busy");
    if (focusPanel) {
      panel.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
      panel.focus({ preventScroll: true });
    }

    fetch(url.toString(), { headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (data) {
        if (id !== requestId) return;
        var items = (data && data.results) || [];
        list.textContent = "";
        items.forEach(function (item) { list.appendChild(buildResult(item)); });
        if (items.length) {
          statusEl.textContent = items.length + (items.length === 1 ? " service found" : " services found");
          show("results");
        } else {
          statusEl.textContent = "No services found";
          show("empty");
        }
      })
      .catch(function () {
        if (id !== requestId) return;
        statusEl.textContent = "";
        show("error");
      })
      .then(function () { if (id === requestId) form.classList.remove("is-busy"); });
  }

  function currentRegion() { return regionSelect ? regionSelect.value : ""; }

  /* The search form */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    run({ q: qInput.value.trim(), region: currentRegion() }, true);
  });

  /* Popular links, category cards, "View professional", area chips: data-q / data-category / data-region */
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    var link = e.target.closest("[data-search-link]");
    if (!link) return;
    e.preventDefault();
    var params = { q: link.getAttribute("data-q") || "", category: link.getAttribute("data-category") || "", region: link.getAttribute("data-region") || currentRegion() };
    if (link.hasAttribute("data-region") && regionSelect) regionSelect.value = params.region;
    if (link.hasAttribute("data-q")) qInput.value = params.q;
    else if (!link.hasAttribute("data-region")) qInput.value = "";
    run(params, true);
  });

  panel.querySelector("[data-results-retry]").addEventListener("click", function () { if (lastParams) run(lastParams, false); });
  panel.querySelector("[data-results-close]").addEventListener("click", function () {
    requestId++;
    panel.hidden = true;
    form.classList.remove("is-busy");
    qInput.focus();
  });
})();
