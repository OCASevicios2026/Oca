/* ============ MODAL DETALLE SERVICIO (servicios.html) ============ */
(function () {
  var modal = document.getElementById('servicioModal');
  var modalClose = document.getElementById('servicioModalClose');
  if (!modal || !window.SERVICIOS_DATOS) return;

  var fotoEl = document.getElementById('modalServicioFoto');
  var numEl = document.getElementById('modalServicioNum');
  var nombreEl = document.getElementById('modalServicioNombre');
  var descEl = document.getElementById('modalServicioDesc');
  var subsEl = document.getElementById('modalSubservicios');
  var ctaEl = document.getElementById('modalServicioCta');

  function abrirModal(key) {
    var servicio = SERVICIOS_DATOS.find(function (s) { return s.key === key; });
    if (!servicio) return;

    fotoEl.src = servicio.foto;
    fotoEl.alt = servicio.nombre;
    numEl.textContent = servicio.num;
    nombreEl.textContent = servicio.nombre;
    descEl.textContent = servicio.desc;

    subsEl.innerHTML = '';
    servicio.subservicios.forEach(function (sub, i) {
      var card = document.createElement('div');
      card.className = 'subservicio-card reveal';
      card.style.setProperty('--stagger', (i * 0.05) + 's');

      var img = document.createElement('img');
      img.src = sub.foto;
      img.alt = sub.nombre;
      img.loading = 'lazy';

      var info = document.createElement('div');
      info.className = 'subservicio-info';

      var h = document.createElement('h4');
      h.textContent = sub.nombre;

      var p = document.createElement('p');
      p.textContent = sub.desc;

      info.appendChild(h);
      info.appendChild(p);
      card.appendChild(img);
      card.appendChild(info);
      subsEl.appendChild(card);
    });

    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(function () {
      modal.classList.add('open');
    });
  }

  function cerrarModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
    setTimeout(function () {
      modal.hidden = true;
    }, 300);
  }

  document.querySelectorAll('.apartado-detalle').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      abrirModal(this.dataset.servicio);
    });
  });

  document.querySelectorAll('.apartado-foto').forEach(function (foto) {
    foto.addEventListener('click', function () {
      var contenido = this.nextElementSibling;
      var boton = contenido ? contenido.querySelector('.apartado-detalle') : null;
      if (boton) abrirModal(boton.dataset.servicio);
    });
  });

  if (modalClose) modalClose.addEventListener('click', cerrarModal);
  modal.addEventListener('click', function (e) {
    if (e.target === modal) cerrarModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.hidden) cerrarModal();
  });
})();
