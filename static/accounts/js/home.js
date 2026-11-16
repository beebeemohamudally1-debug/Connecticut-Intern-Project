/* HandyConnect visitor home: adds a soft shadow to the top bar once the page is scrolled. */
(function () {
  var nav = document.querySelector(".hm-nav");
  if (!nav) return;
  function update() { nav.classList.toggle("is-scrolled", window.scrollY > 4); }
  update();
  window.addEventListener("scroll", update, { passive: true });
})();