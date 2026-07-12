/**
 * accessibility.js — Widget de Accesibilidad AlertaVecinal v3.0
 * ► Ícono ISA clásico (monito de toda la vida)
 * ► Perfiles en grid 2×2 con SVG puro
 * ► Funciones escalables por niveles con puntos indicadores
 * ► Sin emojis — solo SVG
 * ► Ctrl+U para abrir/cerrar
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'av_a11y_v3';

  /* ── SVG Icons ────────────────────────────────────────────────── */
  const ICONS = {
    // Vitruvian Man accessibility icon
    isa: `<svg viewBox="0 0 100 100" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" stroke-width="8"/>
      <circle cx="50" cy="27" r="7"/>
      <path d="M50 36c-5.5 0-20.3 3.4-23.7 5.1-1.3.7-1.8 2.3-1.1 3.6.7 1.3 2.3 1.8 3.6 1.1 2.3-1.1 14.2-3.8 21.2-3.8s18.9 2.7 21.2 3.8c1.3.7 2.9.2 3.6-1.1.7-1.3.2-2.9-1.1-3.6C70.3 39.4 55.5 36 50 36z"/>
      <path d="M46 45v19l-9 16c-.6 1.1-.2 2.6.9 3.2.4.2.8.3 1.2.3.8 0 1.6-.4 2-1.2l9.9-17.6 9.9 17.6c.4.8 1.2 1.2 2 1.2.4 0 .8-.1 1.2-.3 1.1-.6 1.5-2.1.9-3.2l-9-16V45H46z"/>
    </svg>`,

    // Profiles
    epilepsy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>`,
    vision: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>`,
    cognitive: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96-.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 013.32-3.97A2.5 2.5 0 019.5 2z"/>
      <path d="M14.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 004.96-.44 2.5 2.5 0 002.96-3.08 3 3 0 00.34-5.58 2.5 2.5 0 00-3.32-3.97A2.5 2.5 0 0014.5 2z"/>
    </svg>`,
    adhd: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>`,

    // Feature icons
    contrast: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 2a10 10 0 010 20V2z" fill="currentColor"/></svg>`,
    highlight: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>`,
    textSize: `<svg viewBox="0 0 24 24" fill="currentColor"><text x="1" y="18" font-size="13" font-weight="900" font-family="sans-serif">T</text><text x="12" y="21" font-size="11" font-weight="700" font-family="sans-serif">T</text></svg>`,
    spacing: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><path d="M4 10l4 2-4 2"/><path d="M20 10l-4 2 4 2"/><line x1="3" y1="18" x2="21" y2="18"/>`,
    reduceMotion: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><rect x="9" y="8" width="2" height="8" fill="currentColor" stroke="none"/><rect x="13" y="8" width="2" height="8" fill="currentColor" stroke="none"/></svg>`,
    hideImages: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/><line x1="3" y1="3" x2="21" y2="21"/></svg>`,
    dyslexia: `<svg viewBox="0 0 24 24" fill="currentColor"><text x="2" y="19" font-size="17" font-weight="900" font-family="Georgia,serif">Df</text></svg>`,
    cursor: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3l14 9-7 1-4 7z"/></svg>`,
    saturation: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3.5 8h17M3.5 16h17" stroke-dasharray="2 2"/></svg>`,
    readingLine: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="2" y1="11" x2="22" y2="11"/><line x1="2" y1="7" x2="10" y2="7"/><line x1="2" y1="15" x2="14" y2="15"/></svg>`,
    readingMask: `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="0" y="0" width="24" height="7" opacity=".6"/><rect x="0" y="17" width="24" height="7" opacity=".6"/><rect x="0" y="7" width="24" height="10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    tts: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`,
    boldText: `<svg viewBox="0 0 24 24" fill="currentColor"><text x="4" y="20" font-size="19" font-weight="900" font-family="sans-serif">B</text></svg>`,
    alignLeft: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6"  x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></svg>`,
    focusMode: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M3 9V5a2 2 0 012-2h4M15 3h4a2 2 0 012 2v4M21 15v4a2 2 0 01-2 2h-4M9 21H5a2 2 0 01-2-2v-4"/></svg>`,
    lineHeight: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="5" y1="6"  x2="19" y2="6"/><line x1="5" y1="12" x2="19" y2="12"/><line x1="5" y1="18" x2="19" y2="18"/><path d="M2 4l2-2 2 2M2 20l2 2 2-2"/></svg>`,
  };

  /* ── Feature definitions ─────────────────────────────────────── */
  const FEATURES = [
    { id:'contrast',     label:'Contraste',             type:'level', maxLevel:3, hint:['','Alto contraste','Invertido','Amarillo/Negro'] },
    { id:'highlight',    label:'Resaltar\nenlaces',     type:'toggle' },
    { id:'textSize',     label:'Agrandar\ntexto',       type:'level', maxLevel:3, hint:['','+20%','+40%','+60%'] },
    { id:'spacing',      label:'Espaciado\nde texto',   type:'level', maxLevel:3, hint:['','Nivel 1','Nivel 2','Nivel 3'] },
    { id:'reduceMotion', label:'Detener\nanimaciones',  type:'toggle' },
    { id:'hideImages',   label:'Ocultar\nimágenes',     type:'toggle' },
    { id:'dyslexia',     label:'Apto para\ndislexia',   type:'toggle' },
    { id:'cursor',       label:'Cursor',                type:'level', maxLevel:3, hint:['','Grande','Muy grande','Blanco'] },
    { id:'saturation',   label:'Saturación',            type:'level', maxLevel:3, hint:['','Sin color','Baja sat.','Alta sat.'] },
    { id:'readingLine',  label:'Línea de\nlectura',     type:'toggle' },
    { id:'readingMask',  label:'Máscara de\nlectura',   type:'toggle' },
    { id:'tts',          label:'Texto\na voz',          type:'toggle' },
    { id:'boldText',     label:'Texto en\nnegrita',     type:'toggle' },
    { id:'alignLeft',    label:'Alinear\na la izq.',    type:'toggle' },
    { id:'focusMode',    label:'Modo\nenfoque',         type:'toggle' },
    { id:'lineHeight',   label:'Interlineado',          type:'level', maxLevel:3, hint:['','1.5×','2.0×','2.5×'] },
  ];

  /* ── Profile definitions (SVG icons only, no emojis) ─────────── */
  const PROFILES = [
    { id:'p-epilepsy', icon:'epilepsy', color:'#f59e0b', label:'Epilepsia',          desc:'Sin destellos ni movimiento',     fn: s=>{ s.reduceMotion=1; s.saturation=1; } },
    { id:'p-vision',   icon:'vision',   color:'#3b82f6', label:'Visión deteriorada', desc:'Contraste, texto grande, cursor',  fn: s=>{ s.contrast=1; s.textSize=2; s.cursor=1; s.highlight=1; } },
    { id:'p-cognitive',icon:'cognitive',color:'#8b5cf6', label:'Cognitivo',          desc:'Dislexia, espaciado, enlaces',     fn: s=>{ s.dyslexia=1; s.spacing=2; s.highlight=1; s.lineHeight=2; } },
    { id:'p-adhd',     icon:'adhd',     color:'#ef4444', label:'TDAH / ADHD',        desc:'Enfoque y sin distracciones',      fn: s=>{ s.focusMode=1; s.reduceMotion=1; s.alignLeft=1; } },
  ];

  /* ── State ───────────────────────────────────────────────────── */
  function buildDefault() {
    const d = { largeWidget: false };
    FEATURES.forEach(f => { d[f.id] = 0; });
    return d;
  }

  let state = buildDefault();

  function load() {
    try { state = { ...buildDefault(), ...JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}') }; } catch(_){}
  }
  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch(_){}
  }

  /* ── Apply CSS classes ──────────────────────────────────────── */
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
    handleReadingLine(!!state.readingLine);
    handleReadingMask(!!state.readingMask);
    handleTTS(!!state.tts);
    handleFocusSpotlight(!!state.focusMode);
  }

  /* ── Reading line ────────────────────────────────────────────── */
  let rlEl = null;
  function handleReadingLine(on) {
    if (on) {
      if (!rlEl) {
        rlEl = document.createElement('div');
        rlEl.id = 'av-reading-line';
        rlEl.setAttribute('aria-hidden','true');
        document.body.appendChild(rlEl);
        document.addEventListener('mousemove', moveRL);
      }
    } else {
      if (rlEl) { rlEl.remove(); rlEl = null; document.removeEventListener('mousemove', moveRL); }
    }
  }
  function moveRL(e) { if(rlEl) rlEl.style.top = e.clientY + 'px'; }

  /* ── Reading mask ───────────────────────────────────────────── */
  let mTop = null, mBot = null;
  function handleReadingMask(on) {
    if (on) {
      if (!mTop) {
        mTop = Object.assign(document.createElement('div'), {id:'av-mask-top'});
        mBot = Object.assign(document.createElement('div'), {id:'av-mask-bot'});
        mTop.setAttribute('aria-hidden','true');
        mBot.setAttribute('aria-hidden','true');
        document.body.append(mTop, mBot);
        document.addEventListener('mousemove', moveMask);
      }
    } else {
      if (mTop) { mTop.remove(); mBot.remove(); mTop=mBot=null; document.removeEventListener('mousemove', moveMask); }
    }
  }
  function moveMask(e) {
    const z = 40;
    if(mTop) mTop.style.height = Math.max(0, e.clientY - z) + 'px';
    if(mBot) mBot.style.top    = (e.clientY + z) + 'px';
  }

  /* ── TTS ────────────────────────────────────────────────────── */
  let ttsOn = false;
  function handleTTS(on) {
    ttsOn = on;
    if (!on && window.speechSynthesis) window.speechSynthesis.cancel();
  }
  function onTTSClick(e) {
    if (!ttsOn || !window.speechSynthesis) return;
    const el = e.target.closest('p,span,h1,h2,h3,h4,label,td,th,li,button,a');
    if (!el) return;
    const txt = (el.innerText||el.textContent||'').trim();
    if (!txt) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(txt);
    u.lang = 'es-MX';
    window.speechSynthesis.speak(u);
  }

  /* ── Focus Spotlight (JS-driven, no CSS opacity hack) ────────── */
  let spotEl = null, spotActive = false;
  function handleFocusSpotlight(on) {
    spotActive = on;
    if (on) {
      if (!spotEl) {
        spotEl = document.createElement('div');
        spotEl.id = 'av-spotlight';
        spotEl.setAttribute('aria-hidden','true');
        document.body.appendChild(spotEl);
        document.addEventListener('mousemove', moveSpot);
        document.addEventListener('focusin', focusSpot);
      }
    } else {
      if (spotEl) {
        spotEl.remove(); spotEl = null;
        document.removeEventListener('mousemove', moveSpot);
        document.removeEventListener('focusin', focusSpot);
      }
    }
  }
  function moveSpot(e) {
    if (!spotEl) return;
    const x = e.clientX, y = e.clientY;
    spotEl.style.background = `radial-gradient(ellipse 220px 140px at ${x}px ${y}px, transparent 0%, rgba(0,0,0,0.65) 100%)`;
  }
  function focusSpot(e) {
    if (!spotEl || !e.target) return;
    const r = e.target.getBoundingClientRect();
    const cx = r.left + r.width/2, cy = r.top + r.height/2;
    spotEl.style.background = `radial-gradient(ellipse 220px 120px at ${cx}px ${cy}px, transparent 0%, rgba(0,0,0,0.65) 100%)`;
  }

  /* ── Build HTML ─────────────────────────────────────────────── */
  function buildWidget() {
    const wrap = document.createElement('div');
    wrap.id = 'av-a11y-wrapper';
    wrap.setAttribute('role','complementary');
    wrap.setAttribute('aria-label','Menú de Accesibilidad');

    wrap.innerHTML = `
      <!-- Trigger button -->
      <button id="av-a11y-trigger"
        aria-label="Abrir menú de accesibilidad (Ctrl+U)"
        aria-expanded="false"
        aria-controls="av-a11y-panel"
        title="Accesibilidad (Ctrl+U)">
        ${ICONS.isa}
      </button>

      <!-- Panel -->
      <div id="av-a11y-panel"
        role="dialog" aria-modal="false"
        aria-label="Opciones de accesibilidad"
        tabindex="-1">

        <!-- Header -->
        <div class="av-panel-header">
          <span class="av-panel-title">
            <span class="av-title-icon">${ICONS.isa}</span>
            Menú de Accesibilidad
            <kbd>Ctrl+U</kbd>
          </span>
          <button id="av-a11y-close" aria-label="Cerrar menú de accesibilidad">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div class="av-panel-subtitle">Personaliza tu experiencia de navegación</div>

        <!-- Large widget toggle -->
        <div class="av-toggle-row">
          <span>Widget de gran tamaño</span>
          <label class="av-sw" aria-label="Activar widget de gran tamaño">
            <input type="checkbox" id="av-opt-largeWidget">
            <span class="av-sw-track"></span>
          </label>
        </div>

        <!-- Profiles -->
        <div class="av-section-label">Perfiles de Usuario</div>
        <div class="av-profiles-grid" role="group" aria-label="Perfiles predefinidos de accesibilidad">
          ${PROFILES.map(p=>`
            <button class="av-profile-card" id="${p.id}"
              aria-label="${p.label}: ${p.desc}"
              style="--profile-color: ${p.color}">
              <span class="av-profile-icon">${ICONS[p.icon]}</span>
              <span class="av-profile-name">${p.label}</span>
              <span class="av-profile-desc">${p.desc}</span>
            </button>
          `).join('')}
        </div>

        <!-- Options grid -->
        <div class="av-section-label">Ajustes de Accesibilidad</div>
        <div class="av-grid" role="group" aria-label="Ajustes individuales de accesibilidad">
          ${FEATURES.map(f=>`
            <button class="av-opt-btn" id="av-btn-${f.id}"
              aria-pressed="false"
              aria-label="${f.label.replace(/\n/g,' ')}">
              <span class="av-opt-icon">${ICONS[f.id]||''}</span>
              <span class="av-opt-label">${f.label.replace(/\n/g,'<br>')}</span>
              ${f.type==='level'?`<span class="av-level-dots" aria-hidden="true">${
                Array.from({length:f.maxLevel},(_,i)=>`<span class="av-dot-ind" data-i="${i+1}"></span>`).join('')
              }</span>`:''}
            </button>
          `).join('')}
        </div>

        <!-- Footer -->
        <div class="av-panel-footer">
          <button id="av-reset-btn" aria-label="Restablecer todas las opciones">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M3 12a9 9 0 109-9M3 3v4h4"/></svg>
            Restablecer todo
          </button>
        </div>
      </div>

      <div id="av-a11y-overlay" aria-hidden="true"></div>
    `;

    document.body.appendChild(wrap);
  }

  /* ── Panel open/close ────────────────────────────────────────── */
  let panelOpen = false;

  function open() {
    panelOpen = true;
    document.getElementById('av-a11y-panel').classList.add('av-open');
    document.getElementById('av-a11y-overlay').classList.add('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded','true');
    requestAnimationFrame(()=> document.getElementById('av-a11y-panel').focus());
  }
  function close() {
    panelOpen = false;
    document.getElementById('av-a11y-panel').classList.remove('av-open');
    document.getElementById('av-a11y-overlay').classList.remove('av-open');
    document.getElementById('av-a11y-trigger').setAttribute('aria-expanded','false');
    document.getElementById('av-a11y-trigger').focus();
  }
  function toggle() { panelOpen ? close() : open(); }

  /* ── Sync button UI ──────────────────────────────────────────── */
  function syncBtn(f) {
    const btn = document.getElementById(`av-btn-${f.id}`);
    if (!btn) return;
    const val = state[f.id];
    const on  = f.type === 'toggle' ? !!val : val > 0;
    btn.classList.toggle('av-active', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (f.type === 'level') {
      btn.querySelectorAll('.av-dot-ind').forEach(d => {
        d.classList.toggle('av-dot-on', parseInt(d.dataset.i) <= val);
      });
    }
  }

  function syncAll() {
    FEATURES.forEach(syncBtn);
    const lw = document.getElementById('av-opt-largeWidget');
    if (lw) lw.checked = !!state.largeWidget;
  }

  /* ── Connect events ──────────────────────────────────────────── */
  function connectAll() {
    // Feature buttons
    FEATURES.forEach(f => {
      const btn = document.getElementById(`av-btn-${f.id}`);
      if (!btn) return;
      syncBtn(f);
      btn.addEventListener('click', () => {
        if (f.type === 'toggle') {
          state[f.id] = state[f.id] ? 0 : 1;
        } else {
          state[f.id] = (state[f.id] + 1) % (f.maxLevel + 1);
        }
        syncBtn(f);
        applyAll();
        save();
        if (f.type === 'level' && f.hint) {
          const lv = state[f.id];
          toast(lv === 0
            ? `${f.label.replace(/\n/,' ')}: desactivado`
            : `${f.label.replace(/\n/,' ')}: ${f.hint[lv]}`);
        }
      });
    });

    // Large widget checkbox
    const lw = document.getElementById('av-opt-largeWidget');
    lw.checked = !!state.largeWidget;
    lw.addEventListener('change', () => {
      state.largeWidget = lw.checked;
      applyAll();
      save();
    });

    // Profiles
    PROFILES.forEach(p => {
      const btn = document.getElementById(p.id);
      if (!btn) return;
      btn.addEventListener('click', () => {
        state = buildDefault();
        p.fn(state);
        save(); applyAll(); syncAll();
        toast(`Perfil: ${p.label}`);
      });
    });

    // Reset
    document.getElementById('av-reset-btn').addEventListener('click', () => {
      state = buildDefault();
      save(); applyAll(); syncAll();
      toast('Accesibilidad restablecida');
    });

    // Close
    document.getElementById('av-a11y-close').addEventListener('click', close);
    document.getElementById('av-a11y-overlay').addEventListener('click', close);
    document.getElementById('av-a11y-trigger').addEventListener('click', toggle);

    // TTS
    document.addEventListener('click', onTTSClick, true);
  }

  /* ── Toast ───────────────────────────────────────────────────── */
  function toast(msg) {
    let t = document.getElementById('av-mini-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'av-mini-toast';
      t.setAttribute('role','status');
      t.setAttribute('aria-live','polite');
      document.getElementById('av-a11y-wrapper').appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('av-show');
    clearTimeout(t._t);
    t._t = setTimeout(() => t.classList.remove('av-show'), 2400);
  }

  /* ── Keyboard ────────────────────────────────────────────────── */
  function setupKeyboard() {
    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.key.toLowerCase() === 'u') { e.preventDefault(); toggle(); }
      if (e.key === 'Escape' && panelOpen) close();
    });

    // Focus trap inside panel
    document.getElementById('av-a11y-panel').addEventListener('keydown', e => {
      if (e.key !== 'Tab') return;
      const panel = document.getElementById('av-a11y-panel');
      const els = [...panel.querySelectorAll('button:not([disabled]),input,[tabindex]:not([tabindex="-1"])')];
      if (!els.length) return;
      const first = els[0], last = els[els.length-1];
      if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
        e.preventDefault(); (e.shiftKey ? last : first).focus();
      }
    });
  }

  /* ── Inject Styles ───────────────────────────────────────────── */
  function injectStyles() {
    const css = `
      #av-a11y-wrapper {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        --primary: #00C2D1;
        --bg-dark: rgba(20, 26, 38, 0.96);
        --border: rgba(255, 255, 255, 0.12);
        --text: #F8F9FA;
        --text-muted: #94A3B8;
        --shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
      }
      #av-a11y-trigger {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: var(--primary);
        color: #fff;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(0, 194, 209, 0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s;
      }
      #av-a11y-trigger:hover {
        transform: scale(1.1);
        box-shadow: 0 8px 25px rgba(0, 194, 209, 0.6);
      }
      #av-a11y-trigger svg {
        width: 32px;
        height: 32px;
      }
      #av-a11y-panel {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 380px;
        max-width: calc(100vw - 40px);
        max-height: calc(100vh - 130px);
        background: var(--bg-dark);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 24px;
        box-shadow: var(--shadow);
        z-index: 99999;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        opacity: 0;
        transform: scale(0.9) translateY(20px);
        pointer-events: none;
        transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        color: var(--text);
        outline: none;
      }
      #av-a11y-panel.av-open {
        opacity: 1;
        transform: scale(1) translateY(0);
        pointer-events: auto;
      }
      .av-large-widget #av-a11y-panel {
        width: 480px;
        max-height: calc(100vh - 110px);
        font-size: 1.15rem;
      }
      .av-large-widget .av-opt-btn {
        padding: 16px 8px;
        min-height: 100px;
      }
      .av-panel-header {
        padding: 20px 20px 8px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .av-panel-title {
        font-size: 1.25rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .av-title-icon svg {
        width: 24px;
        height: 24px;
        color: var(--primary);
      }
      .av-panel-title kbd {
        background: rgba(255,255,255,0.1);
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 0.75rem;
        margin-left: 8px;
        color: var(--text-muted);
        font-family: inherit;
      }
      #av-a11y-close {
        background: none;
        border: none;
        color: var(--text-muted);
        cursor: pointer;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s, color 0.2s;
      }
      #av-a11y-close:hover {
        background: rgba(255,255,255,0.1);
        color: var(--text);
      }
      #av-a11y-close svg {
        width: 18px;
        height: 18px;
      }
      .av-panel-subtitle {
        padding: 0 20px 16px 20px;
        font-size: 0.85rem;
        color: var(--text-muted);
        border-bottom: 1px solid rgba(255,255,255,0.08);
      }
      .av-toggle-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 20px;
        background: rgba(255,255,255,0.02);
        border-bottom: 1px solid rgba(255,255,255,0.08);
        font-size: 0.9rem;
      }
      .av-sw {
        position: relative;
        display: inline-block;
        width: 46px;
        height: 24px;
        cursor: pointer;
      }
      .av-sw input {
        opacity: 0;
        width: 0;
        height: 0;
      }
      .av-sw-track {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(255,255,255,0.15);
        border-radius: 24px;
        transition: 0.3s;
      }
      .av-sw-track:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        border-radius: 50%;
        transition: 0.3s;
      }
      .av-sw input:checked + .av-sw-track {
        background-color: var(--primary);
      }
      .av-sw input:checked + .av-sw-track:before {
        transform: translateX(22px);
      }
      .av-section-label {
        padding: 18px 20px 8px 20px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-muted);
      }
      .av-profiles-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        padding: 0 20px;
      }
      .av-profile-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        color: var(--text);
      }
      .av-profile-card:hover {
        background: rgba(255,255,255,0.08);
        border-color: var(--profile-color);
        transform: translateY(-2px);
      }
      .av-profile-icon {
        width: 24px;
        height: 24px;
        color: var(--profile-color);
        margin-bottom: 6px;
      }
      .av-profile-icon svg {
        width: 100%;
        height: 100%;
      }
      .av-profile-name {
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 2px;
      }
      .av-profile-desc {
        font-size: 0.75rem;
        color: var(--text-muted);
        line-height: 1.25;
      }
      .av-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        padding: 0 20px 20px 20px;
        overflow-y: auto;
        flex: 1;
      }
      .av-opt-btn {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 14px 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        color: var(--text);
        gap: 6px;
        min-height: 86px;
      }
      .av-opt-btn:hover {
        background: rgba(255,255,255,0.08);
        border-color: var(--primary);
      }
      .av-opt-btn.av-active {
        background: rgba(0, 194, 209, 0.08);
        border-color: var(--primary);
        box-shadow: inset 0 0 10px rgba(0, 194, 209, 0.1);
      }
      .av-opt-icon {
        width: 22px;
        height: 22px;
      }
      .av-opt-icon svg {
        width: 100%;
        height: 100%;
      }
      .av-opt-label {
        font-size: 0.78rem;
        font-weight: 500;
        line-height: 1.3;
      }
      .av-level-dots {
        display: flex;
        gap: 4px;
        margin-top: 2px;
      }
      .av-dot-ind {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: rgba(255,255,255,0.2);
        transition: 0.2s;
      }
      .av-dot-ind.av-dot-on {
        background: var(--primary);
        box-shadow: 0 0 6px var(--primary);
      }
      .av-panel-footer {
        padding: 14px 20px;
        border-top: 1px solid rgba(255,255,255,0.08);
        display: flex;
        justify-content: center;
        background: rgba(0,0,0,0.2);
      }
      #av-reset-btn {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--text);
        padding: 8px 18px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s ease;
      }
      #av-reset-btn:hover {
        background: rgba(255,255,255,0.15);
        border-color: rgba(255,255,255,0.2);
      }
      #av-mini-toast {
        position: fixed;
        bottom: 25px;
        left: 50%;
        transform: translateX(-50%) translateY(40px);
        background: #1e293b;
        color: #fff;
        padding: 10px 20px;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        opacity: 0;
        pointer-events: none;
        transition: transform 0.3s, opacity 0.3s;
        z-index: 100000;
      }
      #av-mini-toast.av-show {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
      }
      #av-a11y-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0,0,0,0.4);
        opacity: 0;
        pointer-events: none;
        z-index: 99998;
        transition: opacity 0.3s;
      }
      #av-a11y-overlay.av-open {
        opacity: 1;
        pointer-events: auto;
      }

      /* ──────────────────────────────────────────────────────────────
         ESTILOS DE ACCESIBILIDAD SOBRE EL DOCUMENTO
         ────────────────────────────────────────────────────────────── */
      .av-contrast-1, .av-contrast-1 * {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-color: #ffffff !important;
        text-shadow: none !important;
        box-shadow: none !important;
      }
      .av-contrast-2 {
        filter: invert(1) hue-rotate(180deg) !important;
      }
      .av-contrast-2 img, .av-contrast-2 video, .av-contrast-2 canvas {
        filter: invert(1) hue-rotate(180deg) !important;
      }
      .av-contrast-3, .av-contrast-3 * {
        background-color: #000000 !important;
        color: #ffff00 !important;
        border-color: #ffff00 !important;
        text-shadow: none !important;
        box-shadow: none !important;
      }
      .av-highlight a, .av-highlight button {
        outline: 3px solid #ffeb3b !important;
        outline-offset: 2px !important;
        background-color: #000000 !important;
        color: #ffffff !important;
        text-decoration: underline !important;
        font-weight: bold !important;
      }
      .av-textSize-1 { font-size: 1.15em !important; }
      .av-textSize-2 { font-size: 1.30em !important; }
      .av-textSize-3 { font-size: 1.45em !important; }
      .av-spacing-1 { letter-spacing: 0.1em !important; word-spacing: 0.15em !important; }
      .av-spacing-2 { letter-spacing: 0.18em !important; word-spacing: 0.25em !important; }
      .av-spacing-3 { letter-spacing: 0.25em !important; word-spacing: 0.35em !important; }
      .av-reduceMotion, .av-reduceMotion * {
        animation: none !important;
        transition: none !important;
      }
      .av-hideImages img, .av-hideImages video, .av-hideImages canvas {
        opacity: 0.05 !important;
        visibility: hidden !important;
      }
      .av-dyslexia, .av-dyslexia * {
        font-family: "Comic Sans MS", "Comic Sans", "Arial Rounded MT Bold", sans-serif !important;
      }
      .av-cursor-1, .av-cursor-1 * {
        cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 24 24' fill='black' stroke='white' stroke-width='1.5'%3E%3Cpath d='M4.5 2v14.5l3.8-3.8 2.2 5.2 2.2-.9-2.2-5.2h5.5L4.5 2z'/%3E%3C/svg%3E"), auto !important;
      }
      .av-cursor-2, .av-cursor-2 * {
        cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='black' stroke='white' stroke-width='1.5'%3E%3Cpath d='M4.5 2v14.5l3.8-3.8 2.2 5.2 2.2-.9-2.2-5.2h5.5L4.5 2z'/%3E%3C/svg%3E"), auto !important;
      }
      .av-cursor-3, .av-cursor-3 * {
        cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='white' stroke='black' stroke-width='1.5'%3E%3Cpath d='M4.5 2v14.5l3.8-3.8 2.2 5.2 2.2-.9-2.2-5.2h5.5L4.5 2z'/%3E%3C/svg%3E"), auto !important;
      }
      .av-saturation-1 { filter: grayscale(1) !important; }
      .av-saturation-2 { filter: saturate(0.5) !important; }
      .av-saturation-3 { filter: saturate(2) !important; }
      #av-reading-line {
        position: fixed;
        left: 0;
        width: 100vw;
        height: 4px;
        background: #ffeb3b;
        box-shadow: 0 0 10px #ffeb3b;
        pointer-events: none;
        z-index: 999999;
      }
      #av-mask-top, #av-mask-bot {
        position: fixed;
        left: 0;
        width: 100vw;
        background: rgba(0, 0, 0, 0.7);
        pointer-events: none;
        z-index: 999999;
      }
      #av-mask-top { top: 0; }
      #av-mask-bot { bottom: 0; }
      #av-spotlight {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 999999;
        background: radial-gradient(ellipse 220px 140px at center, transparent 0%, rgba(0,0,0,0.65) 100%);
      }
      .av-boldText, .av-boldText * {
        font-weight: bold !important;
      }
      .av-alignLeft, .av-alignLeft * {
        text-align: left !important;
      }
      .av-lineHeight-1, .av-lineHeight-1 * { line-height: 1.6 !important; }
      .av-lineHeight-2, .av-lineHeight-2 * { line-height: 2.0 !important; }
      .av-lineHeight-3, .av-lineHeight-3 * { line-height: 2.4 !important; }
    `;
    const styleEl = document.createElement('style');
    styleEl.id = 'av-a11y-styles';
    styleEl.textContent = css;
    document.head.appendChild(styleEl);
  }

  /* ── Init ────────────────────────────────────────────────────── */
  function init() {
    injectStyles();
    load();
    buildWidget();
    applyAll();
    connectAll();
    syncAll();
    setupKeyboard();
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();

})();
