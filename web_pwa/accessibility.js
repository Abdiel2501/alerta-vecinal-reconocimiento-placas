/**
 * accessibility.js — Widget de Accesibilidad AlertaVecinal
 * Replica las funciones de UserWay de forma nativa sin dependencias externas.
 * Atajo de teclado: CTRL+U para abrir/cerrar
 */

(function () {
  'use strict';

  // ─── Estado de las opciones ──────────────────────────────────────────────────
  const STORAGE_KEY = 'av_accessibility';

  const defaultState = {
    highContrast:    false,
    highlightLinks:  false,
    largeText:       false,
    textSpacing:     false,
    reduceMotion:    false,
    hideImages:      false,
    dyslexiaFont:    false,
    bigCursor:       false,
    largeWidget:     false,
  };

  let state = { ...defaultState };

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      state = { ...defaultState, ...saved };
    } catch (_) {}
  }

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_) {}
  }

  // ─── Aplicar clases al <html> ────────────────────────────────────────────────
  function applyAll() {
    const root = document.documentElement;
    const toggle = (cls, active) => root.classList.toggle(cls, active);

    toggle('av-high-contrast',   state.highContrast);
    toggle('av-highlight-links', state.highlightLinks);
    toggle('av-large-text',      state.largeText);
    toggle('av-text-spacing',    state.textSpacing);
    toggle('av-reduce-motion',   state.reduceMotion);
    toggle('av-hide-images',     state.hideImages);
    toggle('av-dyslexia-font',   state.dyslexiaFont);
    toggle('av-big-cursor',      state.bigCursor);
    toggle('av-large-widget',    state.largeWidget);
  }

  // ─── Botón + Panel HTML ──────────────────────────────────────────────────────
  function buildWidget() {
    const wrapper = document.createElement('div');
    wrapper.id = 'av-a11y-wrapper';
    wrapper.setAttribute('role', 'complementary');
    wrapper.setAttribute('aria-label', 'Menú de Accesibilidad');

    wrapper.innerHTML = `
      <!-- Botón flotante -->
      <button id="av-a11y-trigger"
        aria-label="Abrir menú de accesibilidad (Ctrl+U)"
        aria-expanded="false"
        aria-controls="av-a11y-panel"
        title="Accesibilidad (Ctrl+U)">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true">
          <circle cx="12" cy="4" r="2"/>
          <path d="M19 7H5a1 1 0 000 2h5.5l-1.2 5H7a1 1 0 000 2h2l-.8 3.5a1 1 0 001.9.5L11 16h2l.9 4a1 1 0 001.9-.5L15 16h2a1 1 0 000-2h-2.3l-1.2-5H19a1 1 0 000-2z"/>
        </svg>
      </button>

      <!-- Panel lateral -->
      <div id="av-a11y-panel"
        role="dialog"
        aria-modal="false"
        aria-label="Opciones de accesibilidad"
        tabindex="-1">

        <div class="av-panel-header">
          <span class="av-panel-title">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <circle cx="12" cy="4" r="2"/>
              <path d="M19 7H5a1 1 0 000 2h5.5l-1.2 5H7a1 1 0 000 2h2l-.8 3.5a1 1 0 001.9.5L11 16h2l.9 4a1 1 0 001.9-.5L15 16h2a1 1 0 000-2h-2.3l-1.2-5H19a1 1 0 000-2z"/>
            </svg>
            Menú de Accesibilidad
            <kbd>Ctrl+U</kbd>
          </span>
          <button id="av-a11y-close" aria-label="Cerrar menú de accesibilidad">✕</button>
        </div>

        <div class="av-panel-subtitle">
          Personaliza tu experiencia de navegación
        </div>

        <div class="av-toggle-row">
          <span class="av-toggle-label">Widget de gran tamaño</span>
          <label class="av-sw" aria-label="Activar widget de gran tamaño">
            <input type="checkbox" id="av-opt-largeWidget">
            <span class="av-sw-track"></span>
          </label>
        </div>

        <div class="av-grid" role="group" aria-label="Opciones de accesibilidad">

          <button class="av-opt-btn" id="av-opt-highContrast" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 2a10 10 0 010 20V2z" fill="currentColor" stroke="none"/>
              </svg>
            </span>
            <span class="av-opt-label">Contraste +</span>
          </button>

          <button class="av-opt-btn" id="av-opt-highlightLinks" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
              </svg>
            </span>
            <span class="av-opt-label">Resaltar enlaces</span>
          </button>

          <button class="av-opt-btn" id="av-opt-largeText" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <text x="1" y="19" font-size="14" font-weight="bold" font-family="sans-serif">T</text>
                <text x="11" y="22" font-size="18" font-weight="bold" font-family="sans-serif">T</text>
              </svg>
            </span>
            <span class="av-opt-label">Agrandar texto</span>
          </button>

          <button class="av-opt-btn" id="av-opt-textSpacing" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 12h16M4 8l4 4-4 4M20 8l-4 4 4 4"/>
              </svg>
            </span>
            <span class="av-opt-label">Espaciado de texto</span>
          </button>

          <button class="av-opt-btn" id="av-opt-reduceMotion" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="10" y1="15" x2="10" y2="9"/>
                <line x1="14" y1="15" x2="14" y2="9"/>
              </svg>
            </span>
            <span class="av-opt-label">Detener animaciones</span>
          </button>

          <button class="av-opt-btn" id="av-opt-hideImages" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
                <line x1="3" y1="3" x2="21" y2="21"/>
              </svg>
            </span>
            <span class="av-opt-label">Ocultar imágenes</span>
          </button>

          <button class="av-opt-btn" id="av-opt-dyslexiaFont" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <text x="2" y="20" font-size="22" font-weight="bold" font-family="serif">Df</text>
              </svg>
            </span>
            <span class="av-opt-label">Apto para dislexia</span>
          </button>

          <button class="av-opt-btn" id="av-opt-bigCursor" aria-pressed="false">
            <span class="av-opt-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 3l14 9-7 1-4 7z"/>
              </svg>
            </span>
            <span class="av-opt-label">Cursor grande</span>
          </button>

        </div>

        <div class="av-panel-footer">
          <button id="av-reset-btn" aria-label="Restablecer todas las opciones de accesibilidad">
            ↺ Restablecer todo
          </button>
        </div>

      </div>

      <!-- Overlay para cerrar en móvil -->
      <div id="av-a11y-overlay" aria-hidden="true"></div>
    `;

    document.body.appendChild(wrapper);
  }

  // ─── Lógica de apertura/cierre ────────────────────────────────────────────────
  let panelOpen = false;

  function openPanel() {
    panelOpen = true;
    document.getElementById('av-a11y-panel').classList.add('av-open');
    document.getElementById('av-a11y-overlay').classList.add('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded', 'true');
    document.getElementById('av-a11y-panel').focus();
  }

  function closePanel() {
    panelOpen = false;
    document.getElementById('av-a11y-panel').classList.remove('av-open');
    document.getElementById('av-a11y-overlay').classList.remove('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded', 'false');
    document.getElementById('av-a11y-trigger').focus();
  }

  function togglePanel() {
    panelOpen ? closePanel() : openPanel();
  }

  // ─── Conectar botones de opciones ────────────────────────────────────────────
  function connectOption(btnId, stateKey) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    // Estado inicial
    btn.setAttribute('aria-pressed', state[stateKey] ? 'true' : 'false');
    btn.classList.toggle('av-active', state[stateKey]);

    btn.addEventListener('click', () => {
      state[stateKey] = !state[stateKey];
      btn.setAttribute('aria-pressed', state[stateKey] ? 'true' : 'false');
      btn.classList.toggle('av-active', state[stateKey]);
      applyAll();
      saveState();
    });
  }

  // ─── Inicialización ───────────────────────────────────────────────────────────
  function init() {
    loadState();
    buildWidget();
    applyAll();

    // Trigger
    document.getElementById('av-a11y-trigger').addEventListener('click', togglePanel);
    document.getElementById('av-a11y-close').addEventListener('click', closePanel);
    document.getElementById('av-a11y-overlay').addEventListener('click', closePanel);

    // Opciones
    connectOption('av-opt-highContrast',   'highContrast');
    connectOption('av-opt-highlightLinks', 'highlightLinks');
    connectOption('av-opt-largeText',      'largeText');
    connectOption('av-opt-textSpacing',    'textSpacing');
    connectOption('av-opt-reduceMotion',   'reduceMotion');
    connectOption('av-opt-hideImages',     'hideImages');
    connectOption('av-opt-dyslexiaFont',   'dyslexiaFont');
    connectOption('av-opt-bigCursor',      'bigCursor');

    // Toggle de widget grande (checkbox)
    const lwCheck = document.getElementById('av-opt-largeWidget');
    lwCheck.checked = state.largeWidget;
    lwCheck.addEventListener('change', () => {
      state.largeWidget = lwCheck.checked;
      applyAll();
      saveState();
    });

    // Restablecer
    document.getElementById('av-reset-btn').addEventListener('click', () => {
      state = { ...defaultState };
      saveState();
      applyAll();

      // Actualizar UI de botones
      document.querySelectorAll('.av-opt-btn').forEach(btn => {
        btn.classList.remove('av-active');
        btn.setAttribute('aria-pressed', 'false');
      });
      document.getElementById('av-opt-largeWidget').checked = false;
    });

    // Teclado: Ctrl+U para abrir/cerrar
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'u') {
        e.preventDefault();
        togglePanel();
      }
      // Escape para cerrar
      if (e.key === 'Escape' && panelOpen) {
        closePanel();
      }
    });

    // Focus trap dentro del panel
    document.getElementById('av-a11y-panel').addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      const panel = document.getElementById('av-a11y-panel');
      const focusable = panel.querySelectorAll('button, input, [tabindex]:not([tabindex="-1"])');
      const first = focusable[0];
      const last  = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  // Esperar DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
