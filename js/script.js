/* ============ REVEAL ON SCROLL ============ */
(function () {
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale').forEach(function (el) {
    observer.observe(el);
  });
})();

/* ============ NAV SCROLL ============ */
(function () {
  var nav = document.querySelector('nav');
  if (!nav) return;
  function onScroll() {
    if (window.scrollY > 100) {
      nav.classList.add('nav-scrolled');
    } else {
      nav.classList.remove('nav-scrolled');
    }
  }
  window.addEventListener('scroll', onScroll);
})();

/* ============ MENU OVERLAY (hamburguesa) ============ */
(function () {
  var hamburger = document.querySelector('.hamburger');
  var menuOverlay = document.querySelector('.menu-overlay');
  var menuClose = document.querySelector('.menu-overlay-close');
  if (!hamburger || !menuOverlay) return;

  function openMenu() {
    hamburger.classList.add('open');
    menuOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeMenu() {
    hamburger.classList.remove('open');
    menuOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }
  hamburger.addEventListener('click', function () {
    if (menuOverlay.classList.contains('open')) {
      closeMenu();
    } else {
      openMenu();
    }
  });
  if (menuClose) menuClose.addEventListener('click', closeMenu);
  menuOverlay.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', closeMenu);
  });
})();

/* ============ HERO SLIDER (solo index) ============ */
(function () {
  var dots = document.querySelectorAll('.hero-dot');
  if (!dots.length) return;

  var img = document.querySelector('.hero-fondos img');
  var video = document.getElementById('heroVideo');
  var videoWrap = document.querySelector('.hero-video-wrap');
  var heroContent = document.querySelector('.hero-content');
  var heroFondos = document.querySelector('.hero-fondos');
  var nav = document.querySelector('nav');
  var transitioning = false;
  var currentSlide = 0;

  function setNavLogoHidden(hidden) {
    if (!nav) return;
    if (hidden) {
      nav.classList.add('nav-logo-hidden');
    } else {
      nav.classList.remove('nav-logo-hidden');
    }
  }

  function updateHeroScroll() {
    if (currentSlide !== 0) {
      img.style.transform = 'none';
      return;
    }
    var y = window.scrollY;
    var vh = window.innerHeight;
    if (y < vh) {
      var p = y / vh;
      img.style.transform = 'translateY(' + (p * 100) + 'px) scale(' + (1 + p * 0.06) + ')';
      heroContent.style.opacity = String(Math.max(0, 1 - p * 1.4));
      heroContent.style.transform = 'translateY(' + (p * 50) + 'px)';
    } else {
      img.style.transform = 'translateY(100px) scale(1.06)';
      heroContent.style.opacity = '0';
      heroContent.style.transform = 'translateY(50px)';
    }
  }

  function goToSlide(index) {
    if (index === currentSlide || transitioning) return;
    transitioning = true;

    heroContent.style.transition = 'opacity 1s ease, transform 1s cubic-bezier(0.22, 1, 0.36, 1)';

    if (index === 0) {
      videoWrap.style.display = 'none';
      video.pause();
      img.style.transform = 'none';
      img.style.opacity = '1';
      heroContent.style.display = 'block';
      setNavLogoHidden(false);
      setTimeout(function () {
        heroContent.style.opacity = '1';
        heroContent.style.transform = 'none';
        updateHeroScroll();
        transitioning = false;
      }, 900);
    } else {
      heroContent.style.opacity = '0';
      setNavLogoHidden(true);
      img.style.opacity = '0';
      video.currentTime = 0;
      videoWrap.style.display = 'block';
      videoWrap.style.opacity = '0';
      void videoWrap.offsetHeight;
      videoWrap.style.opacity = '1';
      setTimeout(function () {
        video.play();
        heroContent.style.display = 'none';
        transitioning = false;
      }, 1200);
    }

    dots.forEach(function (d) { d.classList.remove('active'); });
    dots[index].classList.add('active');
    currentSlide = index;
  }

  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      goToSlide(parseInt(this.dataset.slide));
    });
  });

  window.addEventListener('scroll', updateHeroScroll);
  window.addEventListener('resize', updateHeroScroll);

  var heroScroll = document.querySelector('.hero-scroll');
  if (heroScroll) {
    heroScroll.addEventListener('click', function () {
      window.scrollTo({ top: window.innerHeight, behavior: 'smooth' });
    });
  }

  setInterval(function () {
    if (currentSlide === 0) {
      goToSlide(1);
    }
  }, 30000);
})();

/* ============ SERVICIOS SLIDER (solo index) ============ */
(function () {
  var serviciosSlider = document.querySelector('.servicios-slider');
  var prevBtn = document.querySelector('.servicios-btn.prev');
  var nextBtn = document.querySelector('.servicios-btn.next');
  if (!serviciosSlider || !prevBtn || !nextBtn) return;

  prevBtn.addEventListener('click', function () {
    serviciosSlider.scrollBy({ left: -(serviciosSlider.clientWidth * 0.8), behavior: 'smooth' });
  });
  nextBtn.addEventListener('click', function () {
    serviciosSlider.scrollBy({ left: serviciosSlider.clientWidth * 0.8, behavior: 'smooth' });
  });

  document.querySelectorAll('.servicio-card').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r = this.getBoundingClientRect();
      this.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      this.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  });
})();
