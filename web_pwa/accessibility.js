/**
 * accessibility.js — Widget de Accesibilidad AlertaVecinal v2.0
 * ► Funciones escalables por niveles (igual que UserWay)
 * ► Texto a voz, línea de lectura, máscara, saturación, perfiles
 * ► Atajo Ctrl+U para abrir/cerrar
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'av_a11y_v2';

  // ─── Definición de features ─────────────────────────────────────────────────
  // type: 'level' => cicla entre 0..maxLevel   (0 = apagado)
  // type: 'toggle' => on/off
  const FEATURES = [
    // ── Nivel 1: contraste ─────
    { id: 'contrast',      label: 'Contraste',        type: 'level',  maxLevel: 3,
      icon: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 2a10 10 0 010 20V2z" fill="currentColor"/></svg>`,
      hint: ['', 'Alto contraste', 'Contraste invertido', 'Amarillo en negro'] },

    // ── Resaltar enlaces ───────
    { id: 'highlight',     label: 'Resaltar\nenlaces', type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>` },

    // ── Nivel 2: texto grande ──
    { id: 'textSize',      label: 'Agrandar\ntexto',   type: 'level',  maxLevel: 3,
      icon: `<svg viewBox="0 0 36 36"><text x="0"  y="28" font-size="22" font-weight="900" font-family="sans-serif" fill="currentColor">T</text><text x="18" y="32" font-size="18" font-weight="700" font-family="sans-serif" fill="currentColor">T</text></svg>`,
      hint: ['', '+20%', '+40%', '+60%'] },

    // ── Nivel 3: espaciado ─────
    { id: 'spacing',       label: 'Espaciado\nde texto', type: 'level', maxLevel: 3,
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12h16M4 8l4 4-4 4M20 8l-4 4 4 4"/></svg>`,
      hint: ['', 'Nivel 1', 'Nivel 2', 'Nivel 3'] },

    // ── Detener animaciones ────
    { id: 'reduceMotion',  label: 'Detener\nanimaciones', type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><rect x="9" y="8" width="2" height="8"/><rect x="13" y="8" width="2" height="8"/></svg>` },

    // ── Ocultar imágenes ───────
    { id: 'hideImages',    label: 'Ocultar\nimágenes',   type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/><line x1="3" y1="3" x2="21" y2="21"/></svg>` },

    // ── Dislexia ───────────────
    { id: 'dyslexia',      label: 'Apto para\ndislexia',  type: 'toggle',
      icon: `<svg viewBox="0 0 36 36"><text x="1" y="30" font-size="28" font-family="Georgia,serif" fill="currentColor" font-weight="bold">Df</text></svg>` },

    // ── Nivel 4: cursor ────────
    { id: 'cursor',        label: 'Cursor',             type: 'level',  maxLevel: 3,
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3l14 9-7 1-4 7z"/></svg>`,
      hint: ['', 'Grande', 'Muy grande', 'Blanco/Grande'] },

    // ── Nivel 5: saturación ───
    { id: 'saturation',    label: 'Saturación',         type: 'level',  maxLevel: 3,
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2v20M2 12h20" stroke-dasharray="3"/></svg>`,
      hint: ['', 'Sin color', 'Baja saturación', 'Alta saturación'] },

    // ── Línea de lectura ───────
    { id: 'readingLine',   label: 'Línea de\nlectura',   type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="12" x2="22" y2="12"/><path d="M2 6h8M2 18h14"/></svg>` },

    // ── Máscara de lectura ─────
    { id: 'readingMask',   label: 'Máscara de\nlectura',  type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="0" y="0" width="24" height="8"/><rect x="0" y="16" width="24" height="8" opacity=".4"/><rect x="0" y="8" width="24" height="8" fill="none" stroke="currentColor" stroke-width="1"/></svg>` },

    // ── Texto a voz ────────────
    { id: 'tts',           label: 'Texto a\nvoz',        type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/></svg>` },

    // ── Negrita ────────────────
    { id: 'boldText',      label: 'Texto\nen negrita',   type: 'toggle',
      icon: `<svg viewBox="0 0 24 24"><text x="4" y="20" font-size="18" font-weight="900" font-family="sans-serif" fill="currentColor">B</text></svg>` },

    // ── Alinear texto ──────────
    { id: 'alignLeft',     label: 'Alinear\ntext izq.',  type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6"  x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></svg>` },

    // ── Bloqueo de enfoque ─────
    { id: 'focusMode',     label: 'Modo\nenfoque',       type: 'toggle',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>` },

    // ── Interlineado ───────────
    { id: 'lineHeight',    label: 'Interlineado',       type: 'level',  maxLevel: 3,
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6"  x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><path d="M2 3l2-2 2 2M2 21l2 2 2-2"/></svg>`,
      hint: ['', '1.5×', '2.0×', '2.5×'] },
  ];

  const PROFILES = [
    {
      id: 'profile-epilepsy',
      label: '⚡ Epilepsia',
      desc: 'Elimina destellos y movimiento',
      fn: (s) => { s.reduceMotion = true; s.saturation = 1; },
    },
    {
      id: 'profile-vision',
      label: '👁 Visión deteriorada',
      desc: 'Contraste máximo, texto grande',
      fn: (s) => { s.contrast = 1; s.textSize = 2; s.cursor = 1; s.highlight = true; },
    },
    {
      id: 'profile-cognitive',
      label: '🧠 Cognitivo',
      desc: 'Dislexia, espaciado, enlaces',
      fn: (s) => { s.dyslexia = true; s.spacing = 2; s.highlight = true; s.lineHeight = 2; },
    },
    {
      id: 'profile-adhd',
      label: '🎯 TDAH / ADHD',
      desc: 'Enfoque y sin distracciones',
      fn: (s) => { s.focusMode = true; s.reduceMotion = true; s.alignLeft = true; },
    },
  ];

  // ─── Estado inicial ─────────────────────────────────────────────────────────
  function buildDefault() {
    const d = { largeWidget: false };
    FEATURES.forEach(f => { d[f.id] = 0; }); // 0 = off para todos
    return d;
  }

  let state = buildDefault();

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      state = { ...buildDefault(), ...saved };
    } catch (_) {}
  }

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_) {}
  }

  // ─── Aplicar CSS al <html> ──────────────────────────────────────────────────
  function applyAll() {
    const root = document.documentElement;
    const tgl  = (cls, on) => root.classList.toggle(cls, !!on);

    FEATURES.forEach(f => {
      if (f.type === 'toggle') {
        tgl(`av-${f.id}`, !!state[f.id]);
      } else {
        for (let i = 1; i <= f.maxLevel; i++) {
          tgl(`av-${f.id}-${i}`, state[f.id] === i);
        }
      }
    });

    tgl('av-large-widget', !!state.largeWidget);

    // Extras que necesitan JS directo
    handleReadingLine(!!state.readingLine);
    handleReadingMask(!!state.readingMask);
    handleTTS(!!state.tts);
  }

  // ─── Línea de lectura ────────────────────────────────────────────────────────
  let readingLineEl = null;
  function handleReadingLine(active) {
    if (active) {
      if (!readingLineEl) {
        readingLineEl = document.createElement('div');
        readingLineEl.id = 'av-reading-line';
        readingLineEl.setAttribute('aria-hidden', 'true');
        document.body.appendChild(readingLineEl);
        document.addEventListener('mousemove', moveReadingLine);
      }
    } else {
      if (readingLineEl) {
        readingLineEl.remove();
        readingLineEl = null;
        document.removeEventListener('mousemove', moveReadingLine);
      }
    }
  }
  function moveReadingLine(e) {
    if (readingLineEl) readingLineEl.style.top = e.clientY + 'px';
  }

  // ─── Máscara de lectura ──────────────────────────────────────────────────────
  let maskTopEl = null, maskBotEl = null;
  function handleReadingMask(active) {
    if (active) {
      if (!maskTopEl) {
        maskTopEl = document.createElement('div');
        maskTopEl.id = 'av-mask-top';
        maskTopEl.setAttribute('aria-hidden', 'true');
        maskBotEl = document.createElement('div');
        maskBotEl.id = 'av-mask-bot';
        maskBotEl.setAttribute('aria-hidden', 'true');
        document.body.appendChild(maskTopEl);
        document.body.appendChild(maskBotEl);
        document.addEventListener('mousemove', moveMask);
      }
    } else {
      if (maskTopEl) {
        maskTopEl.remove(); maskTopEl = null;
        maskBotEl.remove(); maskBotEl = null;
        document.removeEventListener('mousemove', moveMask);
      }
    }
  }
  function moveMask(e) {
    const zone = 40;
    if (maskTopEl)  maskTopEl.style.height  = Math.max(0, e.clientY - zone) + 'px';
    if (maskBotEl)  maskBotEl.style.top     = (e.clientY + zone) + 'px';
  }

  // ─── Texto a voz (TTS) ───────────────────────────────────────────────────────
  let ttsActive = false;
  function handleTTS(active) {
    ttsActive = active;
    if (!active && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }
  function onTTSClick(e) {
    if (!ttsActive) return;
    const el = e.target.closest('button, a, p, span, h1, h2, h3, td, th, label');
    if (!el) return;
    const text = el.innerText || el.textContent;
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text.trim());
    utt.lang = 'es-MX';
    window.speechSynthesis.speak(utt);
  }

  // ─── Construcción del HTML del widget ───────────────────────────────────────
  function buildWidget() {
    const wrapper = document.createElement('div');
    wrapper.id = 'av-a11y-wrapper';
    wrapper.setAttribute('role', 'complementary');
    wrapper.setAttribute('aria-label', 'Menú de Accesibilidad');

    // Ícono: persona en silla de ruedas dinámica (accesible ISO 7001 moderno)
    const personIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="currentColor" aria-hidden="true">
      <circle cx="67" cy="12" r="10"/>
      <path d="M90 85L75 55H52L46 30H24a6 6 0 000 12h14l6 26H28a6 6 0 00-6 6v2a28 28 0 1056 0 28 28 0 00-4-.3zM56 90a16 16 0 110-32 16 16 0 010 32z"/>
    </svg>`;

    wrapper.innerHTML = `
      <button id="av-a11y-trigger"
        aria-label="Abrir menú de accesibilidad (Ctrl+U)"
        aria-expanded="false"
        aria-controls="av-a11y-panel"
        title="Accesibilidad (Ctrl+U)">
        ${personIcon}
      </button>

      <div id="av-a11y-panel"
        role="dialog"
        aria-modal="false"
        aria-label="Opciones de accesibilidad"
        tabindex="-1">

        <!-- Encabezado -->
        <div class="av-panel-header">
          <span class="av-panel-title">
            ${personIcon}
            Menú de Accesibilidad
            <kbd>Ctrl+U</kbd>
          </span>
          <button id="av-a11y-close" aria-label="Cerrar menú de accesibilidad">✕</button>
        </div>

        <!-- Subtítulo -->
        <div class="av-panel-subtitle">Personaliza tu experiencia de navegación</div>

        <!-- Widget grande toggle -->
        <div class="av-toggle-row">
          <span class="av-toggle-label">Widget de gran tamaño</span>
          <label class="av-sw" aria-label="Widget de gran tamaño">
            <input type="checkbox" id="av-opt-largeWidget">
            <span class="av-sw-track"></span>
          </label>
        </div>

        <!-- Perfiles de usuario -->
        <div class="av-section-label">Perfiles de Usuario</div>
        <div class="av-profiles" role="group" aria-label="Perfiles de accesibilidad predefinidos">
          ${PROFILES.map(p => `
            <button class="av-profile-btn" id="${p.id}" aria-label="${p.label}: ${p.desc}">
              <span class="av-profile-name">${p.label}</span>
              <span class="av-profile-desc">${p.desc}</span>
            </button>
          `).join('')}
        </div>

        <!-- Grid de opciones -->
        <div class="av-section-label">Ajustes de Accesibilidad</div>
        <div class="av-grid" role="group" aria-label="Opciones de accesibilidad individuales">
          ${FEATURES.map(f => `
            <button class="av-opt-btn" id="av-btn-${f.id}"
              aria-pressed="false"
              aria-label="${f.label.replace(/\n/g, ' ')}${f.type === 'level' ? ' — nivel 0 de ' + f.maxLevel : ''}">
              <span class="av-opt-icon">${f.icon}</span>
              <span class="av-opt-label">${f.label.replace(/\n/g, '<br>')}</span>
              ${f.type === 'level' ? `<span class="av-level-dots" aria-hidden="true">${
                Array.from({length: f.maxLevel}, (_, i) =>
                  `<span class="av-dot-ind" data-i="${i+1}"></span>`).join('')
              }</span>` : ''}
            </button>
          `).join('')}
        </div>

        <!-- Restablecer -->
        <div class="av-panel-footer">
          <button id="av-reset-btn" aria-label="Restablecer todas las opciones de accesibilidad">
            ↺ &nbsp;Restablecer todo
          </button>
        </div>
      </div>

      <div id="av-a11y-overlay" aria-hidden="true"></div>
    `;

    document.body.appendChild(wrapper);
  }

  // ─── Abrir / cerrar ──────────────────────────────────────────────────────────
  let panelOpen = false;

  function openPanel() {
    panelOpen = true;
    document.getElementById('av-a11y-panel').classList.add('av-open');
    document.getElementById('av-a11y-overlay').classList.add('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => document.getElementById('av-a11y-panel').focus());
  }

  function closePanel() {
    panelOpen = false;
    document.getElementById('av-a11y-panel').classList.remove('av-open');
    document.getElementById('av-a11y-overlay').classList.remove('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded', 'false');
    document.getElementById('av-a11y-trigger').focus();
  }

  function togglePanel() { panelOpen ? closePanel() : openPanel(); }

  // ─── Actualizar UI de un botón ───────────────────────────────────────────────
  function syncBtn(feature) {
    const btn = document.getElementById(`av-btn-${feature.id}`);
    if (!btn) return;
    const val = state[feature.id];
    const on  = feature.type === 'toggle' ? !!val : val > 0;

    btn.classList.toggle('av-active', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');

    if (feature.type === 'level') {
      btn.setAttribute('aria-label',
        `${feature.label.replace(/\n/g,' ')} — nivel ${val} de ${feature.maxLevel}`);
      // Dots
      btn.querySelectorAll('.av-dot-ind').forEach(d => {
        d.classList.toggle('av-dot-on', parseInt(d.dataset.i) <= val);
      });
    }
  }

  function syncAll() {
    FEATURES.forEach(syncBtn);
    // largeWidget checkbox
    const lw = document.getElementById('av-opt-largeWidget');
    if (lw) lw.checked = !!state.largeWidget;
  }

  // ─── Conectar botones ────────────────────────────────────────────────────────
  function connectFeatures() {
    FEATURES.forEach(feature => {
      const btn = document.getElementById(`av-btn-${feature.id}`);
      if (!btn) return;

      syncBtn(feature);

      btn.addEventListener('click', () => {
        if (feature.type === 'toggle') {
          state[feature.id] = state[feature.id] ? 0 : 1;
        } else {
          state[feature.id] = (state[feature.id] + 1) % (feature.maxLevel + 1);
        }
        syncBtn(feature);
        applyAll();
        saveState();

        // Toast de nivel
        if (feature.type === 'level' && feature.hint) {
          const lv = state[feature.id];
          showMiniToast(lv === 0
            ? `${feature.label.replace(/\n/g,' ')}: desactivado`
            : `${feature.label.replace(/\n/g,' ')}: ${feature.hint[lv]}`);
        }
      });
    });

    // largeWidget
    const lwCheck = document.getElementById('av-opt-largeWidget');
    lwCheck.checked = !!state.largeWidget;
    lwCheck.addEventListener('change', () => {
      state.largeWidget = lwCheck.checked;
      applyAll();
      saveState();
    });

    // Perfiles
    PROFILES.forEach(profile => {
      const btn = document.getElementById(profile.id);
      if (!btn) return;
      btn.addEventListener('click', () => {
        state = buildDefault();
        profile.fn(state);
        saveState();
        applyAll();
        syncAll();
        showMiniToast(`Perfil aplicado: ${profile.label}`);
      });
    });

    // Reset
    document.getElementById('av-reset-btn').addEventListener('click', () => {
      state = buildDefault();
      saveState();
      applyAll();
      syncAll();
      showMiniToast('Accesibilidad restablecida');
    });

    // Cerrar
    document.getElementById('av-a11y-close').addEventListener('click', closePanel);
    document.getElementById('av-a11y-overlay').addEventListener('click', closePanel);
    document.getElementById('av-a11y-trigger').addEventListener('click', togglePanel);
  }

  // ─── Mini toast interno del widget ──────────────────────────────────────────
  function showMiniToast(msg) {
    let t = document.getElementById('av-mini-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'av-mini-toast';
      t.setAttribute('role', 'status');
      t.setAttribute('aria-live', 'polite');
      document.getElementById('av-a11y-wrapper').appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('av-show');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('av-show'), 2200);
  }

  // ─── Teclado global ──────────────────────────────────────────────────────────
  function setupKeyboard() {
    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.key.toLowerCase() === 'u') {
        e.preventDefault();
        togglePanel();
      }
      if (e.key === 'Escape' && panelOpen) closePanel();
    });

    // Focus trap
    document.getElementById('av-a11y-panel').addEventListener('keydown', e => {
      if (e.key !== 'Tab') return;
      const panel = document.getElementById('av-a11y-panel');
      const focusable = [...panel.querySelectorAll('button:not([disabled]), input, [tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      }
    });

    // TTS: clic en cualquier elemento
    document.addEventListener('click', onTTSClick, true);
  }

  // ─── Init ────────────────────────────────────────────────────────────────────
  function init() {
    loadState();
    buildWidget();
    applyAll();
    connectFeatures();
    syncAll();
    setupKeyboard();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
