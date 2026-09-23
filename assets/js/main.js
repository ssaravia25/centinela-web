/* =========================================================
   Centinela · main.js  (vanilla, sin dependencias)
   - Menú móvil
   - Reveal on scroll + barras de bloques
   - Formulario de waitlist → Google Sheets (Apps Script)
   - Gráfico YTD 2026 (SVG, animado)
   - Año dinámico
   Un solo script para los 4 idiomas: los textos salen de <html lang>.
   ========================================================= */

/* Lo reescribe tools/sync.py desde tools/site.config.json. No editar a mano. */
/* #config */
var CONFIG = {
  endpoint: "https://script.google.com/macros/s/AKfycbycBob6IgrVoHU1HLW7bqMX-vSrh1Ol3hlp9c5VtVwLPTYi0iDaLJmTbeh-A6fG3feM2Q/exec",
  token: "CKuMmMpDeD7BCH3ehNko3cBCScgvyMXm",
  avisoVersion: "v1 · septiembre 2026"
};
/* #endconfig */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Año dinámico ---------- */
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---------- Menú móvil ---------- */
  var toggle = document.querySelector('.nav__toggle');
  var mobile = document.querySelector('.nav__mobile');
  if (toggle && mobile) {
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      mobile.hidden = !open;
    };
    toggle.addEventListener('click', function () {
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });
    mobile.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { setOpen(false); });
    });
  }

  /* ---------- Reveal on scroll ---------- */
  var revealables = document.querySelectorAll('.reveal, .block');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' });
    revealables.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Formulario de waitlist ---------- */
  var IDIOMA = (document.documentElement.lang || 'es').slice(0, 2);

  var TEXTOS = {
    es: {
      nombre: 'Escribe tu nombre.',
      email: 'Escribe tu email.',
      emailMal: 'Revisa el email: parece que le falta algo.',
      consent: 'Marca la casilla para que podamos avisarte.',
      enviando: 'Enviando…',
      fallo: 'No hemos podido guardar tus datos. Vuelve a intentarlo en unos minutos o, mientras tanto,',
      falloEnlace: 'apúntate a la newsletter'
    },
    en: {
      nombre: 'Please enter your name.',
      email: 'Please enter your email.',
      emailMal: 'Please check your email address: something seems to be missing.',
      consent: 'Tick the box so we can let you know.',
      enviando: 'Sending…',
      fallo: 'We couldn’t save your details. Please try again in a few minutes or, in the meantime,',
      falloEnlace: 'sign up to the newsletter'
    },
    it: {
      nombre: 'Scrivi il tuo nome.',
      email: 'Scrivi la tua email.',
      emailMal: 'Controlla l’email: sembra che manchi qualcosa.',
      consent: 'Spunta la casella per permetterci di avvisarti.',
      enviando: 'Invio in corso…',
      fallo: 'Non siamo riusciti a salvare i tuoi dati. Riprova tra qualche minuto oppure, nel frattempo,',
      falloEnlace: 'iscriviti alla newsletter'
    },
    de: {
      nombre: 'Bitte gib deinen Namen ein.',
      email: 'Bitte gib deine E-Mail-Adresse ein.',
      emailMal: 'Bitte prüfe deine E-Mail-Adresse – da scheint etwas zu fehlen.',
      consent: 'Setz bitte das Häkchen, damit wir dich benachrichtigen können.',
      enviando: 'Wird gesendet…',
      fallo: 'Wir konnten deine Daten nicht speichern. Versuch es in ein paar Minuten noch einmal oder',
      falloEnlace: 'melde dich solange für den Newsletter an'
    }
  };
  var T = TEXTOS[IDIOMA] || TEXTOS.es;
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  var wl = document.getElementById('form-waitlist');
  var wlCaja = wl && wl.closest('.wl');
  if (wl && wlCaja && typeof CONFIG !== 'undefined' && CONFIG.endpoint) {
    var wlOk = wlCaja.querySelector('.wl__ok');
    var wlFallback = wlCaja.querySelector('.wl__fallback');
    var wlMsg = wl.querySelector('.wl__msg');
    var wlBtn = wl.querySelector('button[type="submit"]');
    var newsletterHref = wlFallback.querySelector('a').href;

    // Sin endpoint (o sin JS) se queda el enlace a la newsletter, como antes.
    wl.hidden = false;
    wlFallback.hidden = true;

    var limpiar = function () {
      wlMsg.hidden = true;
      wlMsg.textContent = '';
      wl.querySelectorAll('[aria-invalid]').forEach(function (el) { el.removeAttribute('aria-invalid'); });
    };

    var avisar = function (campo, texto) {
      wlMsg.textContent = texto;
      wlMsg.hidden = false;
      if (campo) {
        campo.setAttribute('aria-invalid', 'true');
        campo.focus();
      }
    };

    var terminar = function () {
      wl.hidden = true;
      wlOk.hidden = false;
      wlOk.focus();
    };

    var fallar = function () {
      wl.dataset.enviando = '0';
      wlBtn.disabled = false;
      wlBtn.textContent = wlBtn.dataset.txt;
      avisar(null, T.fallo + ' ');
      var a = document.createElement('a');
      a.href = newsletterHref;
      a.textContent = T.falloEnlace;
      wlMsg.appendChild(a);
      wlMsg.appendChild(document.createTextNode('.'));
    };

    wl.addEventListener('input', function (e) {
      if (e.target.hasAttribute('aria-invalid')) limpiar();
    });

    wl.addEventListener('submit', function (e) {
      e.preventDefault();
      if (wl.dataset.enviando === '1') return;
      limpiar();

      var f = wl.elements;
      var nombre = f.nombre.value.trim();
      var email = f.email.value.trim();
      if (!nombre) return avisar(f.nombre, T.nombre);
      if (!email) return avisar(f.email, T.email);
      if (!EMAIL.test(email)) return avisar(f.email, T.emailMal);
      if (!f.consent.checked) return avisar(f.consent, T.consent);

      // Trampa para bots: si viene rellena, fingimos éxito y no enviamos nada.
      if (f.web.value) return terminar();

      var datos = {
        form: 'waitlist',
        token: CONFIG.token,
        nombre: nombre,
        email: email,
        consent: 'si',
        lang: IDIOMA,
        aviso_version: CONFIG.avisoVersion,
        pagina: location.pathname
      };

      wl.dataset.enviando = '1';
      wlBtn.dataset.txt = wlBtn.textContent;
      wlBtn.disabled = true;
      wlBtn.textContent = T.enviando;

      var ctrl = 'AbortController' in window ? new AbortController() : null;
      var reloj = setTimeout(function () { if (ctrl) ctrl.abort(); }, 15000);

      // Content-Type text/plain a propósito: mantiene la petición "simple" para
      // que el navegador no lance el preflight OPTIONS, que Apps Script no
      // responde. Si lo cambias a application/json, el formulario deja de
      // funcionar en producción y el fallo NO se ve en local.
      fetch(CONFIG.endpoint, {
        method: 'POST',
        body: JSON.stringify(datos),
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        signal: ctrl ? ctrl.signal : undefined
      }).then(function (r) {
        return r.json();
      }).then(function (j) {
        clearTimeout(reloj);
        // Solo un ok explícito cuenta como alta: un fetch resuelto no basta.
        if (j && j.ok) terminar(); else fallar();
      }).catch(function () {
        clearTimeout(reloj);
        fallar();
      });
    });
  }

  /* =========================================================
     Gráfico YTD 2026 — Centinela v4 (backtest, activos reales) vs SPY
     Datos mensuales reales del backtest 2026: Centinela +13,2% · SPY +11,3%
     (SPY = retorno total real; Centinela = backtest mensual v4).
     ========================================================= */
  var chartEl = document.getElementById('ytd-chart');
  if (chartEl) {
    var months = ['Dic', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul'];
    var centinela = [0, 8.0, 16.6, 10.8, 16.3, 18.7, 13.9, 13.2];
    var spy       = [0, 1.5, 0.6, -4.4, 5.7, 11.2, 10.1, 11.3];

    var W = 640, H = 380;
    var m = { top: 24, right: 52, bottom: 34, left: 40 };
    var iw = W - m.left - m.right;
    var ih = H - m.top - m.bottom;

    var allVals = centinela.concat(spy);
    var vMax = Math.max.apply(null, allVals);
    var vMin = Math.min.apply(null, allVals);
    // Redondeo agradable
    var top = Math.ceil((vMax + 1) / 4) * 4;
    var bottom = Math.floor((vMin - 1) / 4) * 4;

    var x = function (i) { return m.left + (iw * i) / (months.length - 1); };
    var y = function (v) { return m.top + ih * (1 - (v - bottom) / (top - bottom)); };

    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('role', 'img');

    // defs: gradiente de área
    var defs = document.createElementNS(NS, 'defs');
    defs.innerHTML =
      '<linearGradient id="cenFill" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#3FB8AE" stop-opacity="0.28"/>' +
      '<stop offset="100%" stop-color="#3FB8AE" stop-opacity="0"/>' +
      '</linearGradient>';
    svg.appendChild(defs);

    // Líneas de rejilla horizontales + ticks %
    for (var g = bottom; g <= top; g += 4) {
      var gy = y(g);
      var line = document.createElementNS(NS, 'line');
      line.setAttribute('x1', m.left); line.setAttribute('x2', W - m.right);
      line.setAttribute('y1', gy); line.setAttribute('y2', gy);
      line.setAttribute('stroke', g === 0 ? 'rgba(180,205,220,0.28)' : 'rgba(180,205,220,0.08)');
      line.setAttribute('stroke-width', g === 0 ? '1.2' : '1');
      svg.appendChild(line);

      var lbl = document.createElementNS(NS, 'text');
      lbl.setAttribute('x', W - m.right + 8); lbl.setAttribute('y', gy + 4);
      lbl.setAttribute('fill', '#7C8794');
      lbl.setAttribute('font-size', '11');
      lbl.setAttribute('font-family', 'IBM Plex Mono, monospace');
      lbl.textContent = (g > 0 ? '+' : '') + g + '%';
      svg.appendChild(lbl);
    }

    // Etiquetas de meses
    months.forEach(function (mo, i) {
      var t = document.createElementNS(NS, 'text');
      t.setAttribute('x', x(i)); t.setAttribute('y', H - 10);
      t.setAttribute('fill', '#7C8794');
      t.setAttribute('font-size', '11');
      t.setAttribute('font-family', 'IBM Plex Mono, monospace');
      t.setAttribute('text-anchor', 'middle');
      t.textContent = mo;
      svg.appendChild(t);
    });

    var pointsStr = function (arr) {
      return arr.map(function (v, i) { return x(i) + ',' + y(v); }).join(' ');
    };

    // Área bajo Centinela
    var area = document.createElementNS(NS, 'polygon');
    area.setAttribute('points', pointsStr(centinela) + ' ' + x(months.length - 1) + ',' + y(bottom) + ' ' + x(0) + ',' + y(bottom));
    area.setAttribute('fill', 'url(#cenFill)');
    area.setAttribute('opacity', '0');
    svg.appendChild(area);

    // Línea SPY
    var spyLine = document.createElementNS(NS, 'polyline');
    spyLine.setAttribute('points', pointsStr(spy));
    spyLine.setAttribute('fill', 'none');
    spyLine.setAttribute('stroke', '#7C8794');
    spyLine.setAttribute('stroke-width', '1.8');
    spyLine.setAttribute('stroke-dasharray', '4 4');
    spyLine.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(spyLine);

    // Línea Centinela
    var cenLine = document.createElementNS(NS, 'polyline');
    cenLine.setAttribute('points', pointsStr(centinela));
    cenLine.setAttribute('fill', 'none');
    cenLine.setAttribute('stroke', '#3FB8AE');
    cenLine.setAttribute('stroke-width', '2.6');
    cenLine.setAttribute('stroke-linecap', 'round');
    cenLine.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(cenLine);

    // Punto final + etiqueta Centinela
    var addEndLabel = function (arr, color, text, dy) {
      var i = arr.length - 1;
      var c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', x(i)); c.setAttribute('cy', y(arr[i]));
      c.setAttribute('r', '3.6'); c.setAttribute('fill', color);
      svg.appendChild(c);
      var t = document.createElementNS(NS, 'text');
      t.setAttribute('x', x(i) - 6); t.setAttribute('y', y(arr[i]) + dy);
      t.setAttribute('fill', color);
      t.setAttribute('font-size', '13');
      t.setAttribute('font-weight', '600');
      t.setAttribute('font-family', 'IBM Plex Mono, monospace');
      t.setAttribute('text-anchor', 'end');
      t.textContent = text;
      svg.appendChild(t);
    };

    chartEl.appendChild(svg);

    // Animación de dibujado
    var animate = function () {
      [spyLine, cenLine].forEach(function (ln) {
        var len = ln.getTotalLength();
        ln.style.transition = 'none';
        ln.style.strokeDasharray = (ln === spyLine ? '4 4' : len + ' ' + len);
        if (ln !== spyLine) {
          ln.style.strokeDashoffset = len;
          // force reflow
          void ln.getBoundingClientRect();
          ln.style.transition = 'stroke-dashoffset 1.6s cubic-bezier(0.22,1,0.36,1)';
          ln.style.strokeDashoffset = '0';
        }
      });
      area.style.transition = 'opacity 1.4s ease 0.4s';
      area.setAttribute('opacity', '1');
      setTimeout(function () {
        addEndLabel(centinela, '#57C98A', '+13,2%', -10);
        addEndLabel(spy, '#7C8794', '+11,3%', 16);
      }, reduceMotion ? 0 : 900);
    };

    if (reduceMotion || !('IntersectionObserver' in window)) {
      area.setAttribute('opacity', '1');
      addEndLabel(centinela, '#57C98A', '+15,80%', -10);
      addEndLabel(spy, '#7C8794', '−0,14%', 16);
    } else {
      var cio = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { animate(); cio.disconnect(); }
        });
      }, { threshold: 0.35 });
      cio.observe(chartEl);
    }
  }
})();
