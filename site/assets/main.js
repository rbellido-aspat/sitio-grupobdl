// Grupo BDL, interacciones del sitio estático
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Menú móvil
  var toggle = document.querySelector('.menu-toggle');
  var nav = document.getElementById('menu-principal');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.innerHTML = open ? '<i class="fa-solid fa-xmark" aria-hidden="true"></i>' : '<i class="fa-solid fa-bars" aria-hidden="true"></i>';
    });
  }
  document.querySelectorAll('.sub-toggle').forEach(function (b) {
    b.addEventListener('click', function () {
      var li = b.parentElement;
      var open = li.classList.toggle('open');
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  // Página activa en el menú
  var path = location.pathname.replace(/index\.html$/, '');
  document.querySelectorAll('.main-nav a').forEach(function (a) {
    if (a.getAttribute('href') === path) a.setAttribute('aria-current', 'page');
  });

  // Titulares con palabras rotativas
  document.querySelectorAll('.rotator').forEach(function (r) {
    var words = r.querySelectorAll('b');
    if (words.length < 2 || reduce) return;
    var i = 0;
    setInterval(function () {
      var cur = words[i];
      cur.classList.remove('is-on');
      cur.classList.add('is-out');
      setTimeout(function () { cur.classList.remove('is-out'); }, 500);
      i = (i + 1) % words.length;
      words[i].classList.add('is-on');
    }, 2500);
  });

  // Slider
  document.querySelectorAll('[data-slider]').forEach(function (s) {
    var slides = s.querySelectorAll('.slide');
    var dots = s.querySelectorAll('.dots button');
    if (slides.length < 2) { if (dots[0]) dots[0].parentElement.hidden = true; return; }
    var i = 0, timer;
    function go(n) {
      slides[i].classList.remove('is-on'); dots[i].classList.remove('is-on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('is-on'); dots[i].classList.add('is-on');
    }
    function start() { if (!reduce) timer = setInterval(function () { go(i + 1); }, 5000); }
    dots.forEach(function (d, n) { d.addEventListener('click', function () { clearInterval(timer); go(n); start(); }); });
    start();
  });

  // Pestañas
  document.querySelectorAll('[data-tabs]').forEach(function (t) {
    var heads = t.querySelectorAll('.tab-title');
    var panes = t.querySelectorAll('.tab-pane');
    heads.forEach(function (h) {
      h.addEventListener('click', function () {
        heads.forEach(function (x) { x.classList.remove('is-on'); x.setAttribute('aria-selected', 'false'); });
        panes.forEach(function (x) { x.classList.remove('is-on'); });
        h.classList.add('is-on'); h.setAttribute('aria-selected', 'true');
        t.querySelector('[data-pane="' + h.dataset.tab + '"]').classList.add('is-on');
      });
    });
  });

  // Filtro de artículos por categoría
  var filter = document.querySelector('.blog-filter');
  if (filter) {
    filter.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      filter.querySelectorAll('button').forEach(function (x) { x.classList.toggle('is-on', x === b); });
      var cat = b.dataset.cat;
      document.querySelectorAll('.cards .card').forEach(function (c) {
        c.hidden = cat && c.dataset.cats.split('|').indexOf(cat) === -1;
      });
    });
  }
})();
