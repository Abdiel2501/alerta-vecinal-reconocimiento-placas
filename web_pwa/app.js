document.addEventListener('DOMContentLoaded', () => {
  // --- 🌐 CONFIGURACIÓN DE ENTORNO (Google Sign-In) ---
  const CONFIG = {
    // Para activar el inicio de sesión real, pega tu Google Client ID aquí:
    GOOGLE_CLIENT_ID: '540888178617-fvqcrjai0avtn0bv90b4c5dtcjeplsgm.apps.googleusercontent.com', 

    // Credenciales del usuario simulador local (se usa si GOOGLE_CLIENT_ID está vacío)
    MOCK_GOOGLE_USER: {
      name: 'Geovani Lara',
      email: 'geovanilara@example.com'
    }
  };

  // --- 🔒 HELPER: PURE JS SHA-256 (Identical to CryptoJS, Brave Shield proof, cross-browser compatible) ---
  function hashPassword(password) {
    function rotateRight(n, xs) {
      return (n >>> xs) | (n << (32 - xs));
    }
    const maxWord = Math.pow(2, 32);
    const h = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ];
    const k = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];

    let ascii = unescape(encodeURIComponent(password));
    const words = [];
    const asciiLength = ascii.length * 8;
    ascii += '\x80';
    while (ascii.length % 64 - 56) ascii += '\x00';
    for (let i = 0; i < ascii.length; i++) {
      words[i >> 2] |= ascii.charCodeAt(i) << (24 - (i % 4) * 8);
    }
    words[words.length] = ((asciiLength / maxWord) | 0);
    words[words.length] = (asciiLength | 0);

    for (let j = 0; j < words.length; j += 16) {
      const w = [];
      let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], h_val = h[7];
      for (let i = 0; i < 64; i++) {
        if (i < 16) {
          w[i] = words[j + i];
        } else {
          const s0 = rotateRight(w[i - 15], 7) ^ rotateRight(w[i - 15], 18) ^ (w[i - 15] >>> 3);
          const s1 = rotateRight(w[i - 2], 17) ^ rotateRight(w[i - 2], 19) ^ (w[i - 2] >>> 10);
          w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
        }

        const ch = (e & f) ^ (~e & g);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const temp1 = (h_val + (rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)) + ch + k[i] + w[i]) | 0;
        const temp2 = ((rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)) + maj) | 0;

        h_val = g;
        g = f;
        f = e;
        e = (d + temp1) | 0;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) | 0;
      }

      h[0] = (h[0] + a) | 0;
      h[1] = (h[1] + b) | 0;
      h[2] = (h[2] + c) | 0;
      h[3] = (h[3] + d) | 0;
      h[4] = (h[4] + e) | 0;
      h[5] = (h[5] + f) | 0;
      h[6] = (h[6] + g) | 0;
      h[7] = (h[7] + h_val) | 0;
    }

    let result = '';
    for (let i = 0; i < 8; i++) {
      const value = h[i];
      for (let j = 3; j >= 0; j--) {
        result += ((value >> (j * 8)) & 255).toString(16).padStart(2, '0');
      }
    }
    return result;
  }

  // DOM Elements - Navigation & Shells
  const splashScreen = document.getElementById('splash-screen');
  const loginScreen = document.getElementById('login-screen');
  const appLayout = document.getElementById('app-layout');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const views = document.querySelectorAll('.view-section');
  const demoBadge = document.getElementById('demoBadge');
  const wsStatusDot = document.getElementById('wsStatusDot');
  const wsStatusText = document.getElementById('wsStatusText');
  const toast = document.getElementById('toast-notification');

  // DOM Elements - Login
  const authLoginForm = document.getElementById('authLoginForm');
  const authRegisterForm = document.getElementById('authRegisterForm');
  const toRegisterBtn = document.getElementById('toRegisterBtn');
  const toLoginBtn = document.getElementById('toLoginBtn');
  const registerName = document.getElementById('registerName');
  const registerEmail = document.getElementById('registerEmail');
  const registerPassword = document.getElementById('registerPassword');
  const submitRegisterBtn = document.getElementById('submitRegisterBtn');

  // Elementos de validación de contraseña
  const passwordStrengthWrapper = document.getElementById('password-strength-wrapper');
  const strengthSegment1 = document.getElementById('strength-segment-1');
  const strengthSegment2 = document.getElementById('strength-segment-2');
  const strengthSegment3 = document.getElementById('strength-segment-3');
  const strengthLabel = document.getElementById('strength-label');
  const reqLength = document.getElementById('req-length');
  const reqUppercase = document.getElementById('req-uppercase');
  const reqNumber = document.getElementById('req-number');
  const reqDot = document.getElementById('req-dot');

  const loginEmail = document.getElementById('loginEmail');
  const loginPassword = document.getElementById('loginPassword');
  const normalLoginBtn = document.getElementById('normalLoginBtn');
  const googleLoginBtn = document.getElementById('googleLoginBtn');
  const googleBtnContainer = document.getElementById('googleBtnContainer');
  const googleBtnContainerRegister = document.getElementById('googleBtnContainerRegister');
  const googleProfileCard = document.getElementById('googleProfileCard');
  const profileName = document.getElementById('profileName');
  const profileEmail = document.getElementById('profileEmail');
  const userInitial = document.getElementById('userInitial');
  const logoutBtn = document.getElementById('logoutBtn');

  // DOM Elements - Dual Lens Cameras
  const videoCanvasFixed = document.getElementById('videoCanvasFixed');
  const ctxFixed = videoCanvasFixed.getContext('2d');
  const videoCanvasPtz = document.getElementById('videoCanvasPtz');
  const ctxPtz = videoCanvasPtz.getContext('2d');
  
  const lensFixedContainer = document.getElementById('lensFixedContainer');
  const lensPtzContainer = document.getElementById('lensPtzContainer');
  const toggleFixedBtn = document.getElementById('toggleFixedBtn');
  const togglePtzBtn = document.getElementById('togglePtzBtn');
  const placeholderFixed = document.getElementById('placeholderFixed');
  const placeholderPtz = document.getElementById('placeholderPtz');
  const videoSpinner = document.getElementById('videoSpinner');
  const ptzMsg = document.getElementById('ptzMsg');
  const recIndicator = document.getElementById('liveDot');
  const videoMetaText = document.getElementById('videoMetaText');

  // DOM Elements - PTZ & Zoom Overlay
  const ptzOverlay = document.getElementById('ptzOverlay');
  const zoomOverlay = document.getElementById('zoomOverlay');
  const ptzDirs = document.querySelectorAll('.ptz-dir');
  const zoomBtns = document.querySelectorAll('.zoom-btn');
  const ptzCenterBtn = document.getElementById('ptzCenterBtn');

  // DOM Elements - Quick Tools
  const toolTalk = document.getElementById('toolTalk');
  const toolListen = document.getElementById('toolListen');
  const toolCapture = document.getElementById('toolCapture');
  const toolAi = document.getElementById('toolAi');

  // DOM Elements - Settings & Config
  const listCamerasBtn = document.getElementById('listCamerasBtn');
  const rtspUrlInput = document.getElementById('rtspUrl');
  const useWebcamBtn = document.getElementById('useWebcamBtn');
  const applyRtspBtn = document.getElementById('applyRtspBtn');
  const activeCameraInfo = document.getElementById('activeCameraInfo');
  
  const serverIpInput = document.getElementById('serverIp');
  const serverPortInput = document.getElementById('serverPort');
  const connectBtn = document.getElementById('connectBtn');
  
  const telegramTokenInput = document.getElementById('telegramToken');
  const telegramChatIdInput = document.getElementById('telegramChatId');
  const saveTelegramBtn = document.getElementById('saveTelegramBtn');
  const telegramAdminSection = document.getElementById('telegramAdminSection');
  const telegramUserSection = document.getElementById('telegramUserSection');
  const telegramBotLink = document.getElementById('telegramBotLink');
  const telegramBotMissing = document.getElementById('telegramBotMissing');
  const showPasswordCheckbox = document.getElementById('showPasswordCheckbox');
  const lensSelector = document.getElementById('lensSelector');
  
  const demoModeToggle = document.getElementById('demoModeToggle');
  const triggerDemoAlertBtn = document.getElementById('triggerDemoAlertBtn');

  // DOM Elements - Alerts & History
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const historyTableBody = document.getElementById('historyTableBody');
  const mobileHistoryList = document.getElementById('mobileHistoryList');

  // DOM Elements - Modals
  const criticalAlertModal = document.getElementById('criticalAlertModal');
  const criticalPlate = document.getElementById('criticalPlate');
  const criticalModel = document.getElementById('criticalModel');
  const criticalColor = document.getElementById('criticalColor');
  const criticalOwner = document.getElementById('criticalOwner');
  const criticalTime = document.getElementById('criticalTime');
  const dismissAlertBtn = document.getElementById('dismissAlertBtn');

  const cameraSelectModal = document.getElementById('cameraSelectModal');
  const cameraListContainer = document.getElementById('cameraListContainer');
  const closeCameraModalBtn = document.getElementById('closeCameraModalBtn');

  // DOM Elements - User Guide Modal
  const userGuideModal = document.getElementById('userGuideModal');
  const userGuideBtn = document.getElementById('userGuideBtn');
  const closeGuideBtn = document.getElementById('closeGuideBtn');
  const prevGuideBtn = document.getElementById('prevGuideBtn');
  const nextGuideBtn = document.getElementById('nextGuideBtn');
  const guideSlides = document.querySelectorAll('.guide-slide');
  const guideDots = document.querySelectorAll('.guide-dot');

  // App State Variables
  let ws = null;
  let currentGuideSlide = 0;
  let reconnectTimeout = null;
  let userDisconnected = false;
  let demoMode = false;
  let isAiActive = true;
  let currentUserEmail = '';
  let currentTheme = 'dark';
  let isAdmin = false;

  // --- USER PREFERENCES STATE ---
  let prefAlarmSound = true;
  let prefBrowserNotif = false;
  let prefVibration = true;
  let prefStartView = 'view-monitor';
  let prefShowFps = true;
  let prefMaxHistory = 100;
  let prefTimeFormat = '24';
  let prefFilterStolen = false;
  let prefLanguage = 'es';
  let prefTimezone = 'America/Mexico_City';
  let prefFontSize = 14;

  // --- SaaS Data Isolation Helpers ---
  function getUserKey(baseKey) {
    if (currentUserEmail) {
      return `${baseKey}_${currentUserEmail}`;
    }
    return baseKey;
  }

  function getLocalItem(key, defaultValue = '') {
    return localStorage.getItem(getUserKey(key)) || defaultValue;
  }

  function setLocalItem(key, value) {
    localStorage.setItem(getUserKey(key), value);
  }
  
  // PTZ Simulated coordinates offset
  let ptzOffsetX = 0;
  let ptzOffsetY = 0;
  let demoZoomScale = 1.0;
  
  // Animation intervals
  let demoCanvasInterval = null;
  let demoAlertInterval = null;
  let fixedLensInterval = null;
  let demoPlateIndex = 0;
  let lastDemoAlertTime = 0;
  let lastDemoPlate = '';

  // Load cache from localStorage
  let history = [];
  let demoHistory = [];
  serverIpInput.value = getLocalItem('server_ip', '127.0.0.1');
  serverPortInput.value = getLocalItem('server_port', '8765');
  if (telegramTokenInput) telegramTokenInput.value = getLocalItem('telegram_token', '');
  if (telegramChatIdInput) telegramChatIdInput.value = getLocalItem('telegram_chat_id', '');

  // --- 💬 FLOATING TOAST NOTIFICATION ---
  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3000);
  }

  // --- 🌀 SPLASH SCREEN & AUTH LOGIC ---
  const privacyConsentModal = document.getElementById('privacyConsentModal');
  const acceptConsentBtn = document.getElementById('acceptConsentBtn');
  const declineConsentBtn = document.getElementById('declineConsentBtn');

  // Legal Modal DOM elements
  const legalTabTermsBtn = document.getElementById('legalTabTermsBtn');
  const legalTabPrivacyBtn = document.getElementById('legalTabPrivacyBtn');
  const legalTermsPane = document.getElementById('legalTermsPane');
  const legalPrivacyPane = document.getElementById('legalPrivacyPane');
  const legalConsentCheckbox = document.getElementById('legalConsentCheckbox');

  // Lanzamiento de la pantalla de carga (Splash Screen) por 2 segundos
  setTimeout(() => {
    splashScreen.classList.add('fade-out');
    
    const privacyAccepted = localStorage.getItem('privacy_accepted') === 'true';
    if (!privacyAccepted) {
      privacyConsentModal.classList.add('active');
    } else {
      checkSessionAndStart();
    }
  }, 2000);

  // --- 🔒 SEGURIDAD DE ACCESO Y CIFRADO ---
  let sessionCryptoKey = sessionStorage.getItem('session_crypto_key') || null;
  let authFailures = parseInt(localStorage.getItem('auth_failures') || '0');
  let lockoutTimestamp = parseInt(localStorage.getItem('lockout_timestamp') || '0');
  const loginLockoutError = document.getElementById('loginLockoutError');
  const lockoutTimerSpan = document.getElementById('lockoutTimer');
  let lockoutInterval = null;

  function deriveSessionKey(passphrase) {
    try {
      const salt = CryptoJS.enc.Hex.parse('1a7c8e9b0d2f4e3c');
      const key = CryptoJS.PBKDF2(passphrase, salt, {
        keySize: 256 / 32,
        iterations: 1000
      });
      sessionCryptoKey = key.toString();
      sessionStorage.setItem('session_crypto_key', sessionCryptoKey);
    } catch (e) {
      console.error("Error derivando clave simétrica:", e);
    }
  }

  function checkLockout() {
    if (lockoutTimestamp > 0) {
      const now = Date.now();
      const timePassed = now - lockoutTimestamp;
      const cooldown = 5 * 60 * 1000; // 5 minutos
      
      if (timePassed < cooldown) {
        const secondsLeft = Math.ceil((cooldown - timePassed) / 1000);
        normalLoginBtn.disabled = true;
        loginLockoutError.style.display = 'block';
        lockoutTimerSpan.textContent = secondsLeft;
        
        if (!lockoutInterval) {
          lockoutInterval = setInterval(() => {
            const currentNow = Date.now();
            const currentPassed = currentNow - lockoutTimestamp;
            if (currentPassed >= cooldown) {
              clearInterval(lockoutInterval);
              lockoutInterval = null;
              normalLoginBtn.disabled = false;
              loginLockoutError.style.display = 'none';
              authFailures = 0;
              lockoutTimestamp = 0;
              localStorage.removeItem('auth_failures');
              localStorage.removeItem('lockout_timestamp');
            } else {
              lockoutTimerSpan.textContent = Math.ceil((cooldown - currentPassed) / 1000);
            }
          }, 1000);
        }
        return true;
      } else {
        normalLoginBtn.disabled = false;
        loginLockoutError.style.display = 'none';
        authFailures = 0;
        lockoutTimestamp = 0;
        localStorage.removeItem('auth_failures');
        localStorage.removeItem('lockout_timestamp');
      }
    }
    return false;
  }

  // Verificar estado de bloqueo al cargar
  checkLockout();

  // --- 🗝️ INICIALIZAR GOOGLE SIGN-IN ---
  function initGoogleSignIn() {
    if (CONFIG.GOOGLE_CLIENT_ID) {
      if (googleLoginBtn) googleLoginBtn.style.display = 'none';
      if (googleBtnContainer) googleBtnContainer.style.display = 'flex';
      if (googleBtnContainerRegister) googleBtnContainerRegister.style.display = 'flex';

      try {
        google.accounts.id.initialize({
          client_id: CONFIG.GOOGLE_CLIENT_ID,
          callback: handleGoogleCredentialResponse
        });

        // 1. Renderizar botón para Iniciar Sesión con Google
        google.accounts.id.renderButton(
          googleBtnContainer,
          {
            theme: 'outline',
            size: 'large',
            width: 320,
            text: 'signin_with',
            locale: 'es',
            shape: 'rectangular'
          }
        );

        // 2. Renderizar botón para Registrarse con Google
        if (googleBtnContainerRegister) {
          google.accounts.id.renderButton(
            googleBtnContainerRegister,
            {
              theme: 'outline',
              size: 'large',
              width: 320,
              text: 'signup_with',
              locale: 'es',
              shape: 'rectangular'
            }
          );
        }
      } catch (err) {
        console.error("Error inicializando Google Sign-In real:", err);
        if (googleLoginBtn) googleLoginBtn.style.display = 'flex';
        if (googleBtnContainer) googleBtnContainer.style.display = 'none';
        if (googleBtnContainerRegister) googleBtnContainerRegister.style.display = 'none';
      }
    } else {
      if (googleLoginBtn) googleLoginBtn.style.display = 'flex';
      if (googleBtnContainer) googleBtnContainer.style.display = 'none';
      if (googleBtnContainerRegister) googleBtnContainerRegister.style.display = 'none';
    }
  }

  // Ejecutar inicialización al cargar scripts de Google
  if (window.google && window.google.accounts) {
    initGoogleSignIn();
  } else {
    window.addEventListener('load', initGoogleSignIn);
  }

  function checkSessionAndStart() {
    const savedSession = JSON.parse(localStorage.getItem('user_session'));
    if (savedSession) {
      if (!sessionCryptoKey) {
        localStorage.removeItem('user_session');
        loginScreen.style.display = 'flex';
        appLayout.style.display = 'none';
        showToast('🔒 Sesión expirada por inactividad. Inicie sesión de nuevo.');
      } else {
        logInSuccess(savedSession);
      }
    } else {
      loginScreen.style.display = 'flex';
      appLayout.style.display = 'none';
    }
  }

  // --- 📜 INTERACCIONES DEL MODAL LEGAL (Términos y Privacidad) ---
  if (legalTabTermsBtn && legalTabPrivacyBtn) {
    legalTabTermsBtn.addEventListener('click', () => {
      legalTabTermsBtn.classList.add('active');
      legalTabPrivacyBtn.classList.remove('active');
      legalTermsPane.classList.add('active');
      legalPrivacyPane.classList.remove('active');
    });

    legalTabPrivacyBtn.addEventListener('click', () => {
      legalTabPrivacyBtn.classList.add('active');
      legalTabTermsBtn.classList.remove('active');
      legalPrivacyPane.classList.add('active');
      legalTermsPane.classList.remove('active');
    });
  }

  if (legalConsentCheckbox) {
    legalConsentCheckbox.addEventListener('change', () => {
      acceptConsentBtn.disabled = !legalConsentCheckbox.checked;
    });
  }

  acceptConsentBtn.addEventListener('click', () => {
    if (legalConsentCheckbox && !legalConsentCheckbox.checked) {
      alert('Debe marcar la casilla de aceptación para continuar.');
      return;
    }
    localStorage.setItem('privacy_accepted', 'true');
    privacyConsentModal.classList.remove('active');
    checkSessionAndStart();
  });

  declineConsentBtn.addEventListener('click', () => {
    alert('Debe aceptar los Términos de Uso y el Aviso de Privacidad para ingresar y utilizar la plataforma AlertaVecinal.');
  });

  function loadUserSettings(session) {
    currentUserEmail = session.email.toLowerCase().replace(/[^a-z0-9]/g, '_');
    
    // Cargar configuraciones aisladas
    serverIpInput.value = getLocalItem('server_ip', '127.0.0.1');
    serverPortInput.value = getLocalItem('server_port', '8765');
    if (telegramTokenInput) telegramTokenInput.value = getLocalItem('telegram_token', '');
    if (telegramChatIdInput) telegramChatIdInput.value = getLocalItem('telegram_chat_id', '');
    
    // Cargar historial
    history = loadHistoryEncrypted();
    
    // Cargar tema del usuario
    const savedTheme = getLocalItem('theme', '');
    if (savedTheme) {
      currentTheme = savedTheme;
      document.documentElement.setAttribute('data-theme', currentTheme);
      updateThemeIcon(currentTheme);
    }
  }

  function logInSuccess(session) {
    localStorage.setItem('user_session', JSON.stringify(session));
    
    // Determinar si el usuario que inicia sesion es administrador
    isAdmin = session.email && session.email.toLowerCase() === 'admin@alertavecinal.com';

    // Mostrar/ocultar el panel de administracion segun el rol
    const adminPanel = document.getElementById('adminPanel');
    if (adminPanel) {
      adminPanel.style.display = isAdmin ? 'block' : 'none';
    }
    if (telegramAdminSection) {
      telegramAdminSection.style.display = isAdmin ? 'block' : 'none';
    }

    // Actualizar badge de rol en la tarjeta de perfil
    const userRoleBadge = document.getElementById('userRoleBadge');
    if (userRoleBadge) {
      userRoleBadge.textContent = isAdmin ? 'Administrador 🔐' : 'Operador Vecinal';
      userRoleBadge.style.background = isAdmin ? 'linear-gradient(135deg, #ff6b35, #f7c59f)' : '';
      userRoleBadge.style.color = isAdmin ? '#1a1a1a' : '';
    }

    // Cargar y aislar configuraciones del usuario
    loadUserSettings(session);

    // Cargar y aplicar preferencias personalizadas del usuario
    loadUserPreferences();
    applyUserPreferences();
    wireUserPreferencesListeners();

    loginScreen.style.display = 'none';
    appLayout.style.display = 'flex';

    if (session.provider === 'google') {
      googleProfileCard.style.display = 'block';
      profileName.textContent = session.name;
      profileEmail.textContent = session.email;
      if (session.picture) {
        userInitial.innerHTML = `<img src="${session.picture}" alt="${session.name}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
      } else {
        userInitial.textContent = session.name.charAt(0);
      }
    } else {
      googleProfileCard.style.display = 'none';
    }

    showToast(`👋 ¡Bienvenido de nuevo, ${session.name}!`);
    
    // Iniciar renderizado estático del lente fijo
    startFixedLensRender();

    // Iniciar conexión automática (para todos los usuarios, en segundo plano)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('demo') === 'true' || demoModeToggle.checked) {
      demoModeToggle.checked = true;
      startDemoMode();
    } else {
      renderHistory();
      setTimeout(connectWebSocket, 500);
    }

    // Mostrar guía automáticamente a usuarios nuevos
    const guideSeen = getLocalItem('user_guide_seen') === 'true';
    if (!guideSeen) {
      setTimeout(() => {
        openUserGuide();
      }, 800);
    }
  }

  // --- 🔄 TOGGLE ENTRE INICIO DE SESIÓN Y REGISTRO ---
  if (toRegisterBtn && toLoginBtn && authLoginForm && authRegisterForm) {
    toRegisterBtn.addEventListener('click', (e) => {
      e.preventDefault();
      authLoginForm.style.display = 'none';
      authRegisterForm.style.display = 'flex';
    });

    toLoginBtn.addEventListener('click', (e) => {
      e.preventDefault();
      authRegisterForm.style.display = 'none';
      authLoginForm.style.display = 'flex';
    });
  }

  // --- 🔒 VALIDACIÓN DE CONTRASEÑA EN TIEMPO REAL ---
  let isPasswordValid = false;

  function updateReqIndicator(element, met, text) {
    if (!element) return;
    if (met) {
      element.innerHTML = '✔️ ' + text;
      element.style.color = '#81c784';
    } else {
      element.innerHTML = '❌ ' + text;
      element.style.color = '#ff6b6b';
    }
  }

  if (registerPassword && passwordStrengthWrapper) {
    registerPassword.addEventListener('input', () => {
      const val = registerPassword.value;
      
      if (val.length === 0) {
        passwordStrengthWrapper.style.display = 'none';
        isPasswordValid = false;
        return;
      }

      passwordStrengthWrapper.style.display = 'block';
      
      const hasLength = val.length >= 8;
      const hasUppercase = /[A-Z]/.test(val);
      const hasNumber = /[0-9]/.test(val);
      const hasSpecial = /[^A-Za-z0-9]/.test(val);

      // Actualizar checklist
      updateReqIndicator(reqLength, hasLength, 'Mínimo 8 caracteres');
      updateReqIndicator(reqUppercase, hasUppercase, 'Al menos 1 mayúscula');
      updateReqIndicator(reqNumber, hasNumber, 'Al menos 1 número');
      updateReqIndicator(reqDot, hasSpecial, 'Al menos 1 símbolo (ej. !@#.)');

      // Calcular fuerza (segmentos)
      let score = 0;
      if (hasLength) score++;
      if (hasUppercase) score++;
      if (hasNumber) score++;
      if (hasSpecial) score++;

      // Resetear colores
      strengthSegment1.style.backgroundColor = 'transparent';
      strengthSegment2.style.backgroundColor = 'transparent';
      strengthSegment3.style.backgroundColor = 'transparent';

      if (score < 2) {
        strengthSegment1.style.backgroundColor = '#ff6b6b';
        strengthLabel.textContent = 'Fuerza: Débil';
        strengthLabel.style.color = '#ff6b6b';
        isPasswordValid = false;
      } else if (score < 4) {
        strengthSegment1.style.backgroundColor = '#ffb700';
        strengthSegment2.style.backgroundColor = '#ffb700';
        strengthLabel.textContent = 'Fuerza: Media';
        strengthLabel.style.color = '#ffb700';
        isPasswordValid = false;
      } else {
        strengthSegment1.style.backgroundColor = '#2e7d32';
        strengthSegment2.style.backgroundColor = '#2e7d32';
        strengthSegment3.style.backgroundColor = '#2e7d32';
        strengthLabel.textContent = 'Fuerza: Fuerte (Segura) ✔️';
        strengthLabel.style.color = '#81c784';
        isPasswordValid = true;
      }
    });
  }

  // --- 💾 REGISTRO DE NUEVO VECINO ---
  if (submitRegisterBtn) {
    submitRegisterBtn.addEventListener('click', () => {
      submitRegisterBtn.disabled = true;

      const name = registerName.value.trim();
      const email = registerEmail.value.trim();
      const password = registerPassword.value.trim();

      if (!name || !email || !password) {
        alert('Por favor complete todos los campos.');
        submitRegisterBtn.disabled = false;
        return;
      }

      if (!isPasswordValid) {
        alert('La contraseña no cumple con todos los requisitos de seguridad.');
        submitRegisterBtn.disabled = false;
        return;
      }

      if (email.toLowerCase() === 'admin@alertavecinal.com') {
        alert('Este correo ya está registrado como administrador.');
        submitRegisterBtn.disabled = false;
        return;
      }

      let registeredUsers = [];
      try {
        registeredUsers = JSON.parse(localStorage.getItem('registered_users') || '[]');
        if (!Array.isArray(registeredUsers)) registeredUsers = [];
      } catch (err) {
        registeredUsers = [];
      }

      const userExists = registeredUsers.some(u => u.email.toLowerCase() === email.toLowerCase());
      if (userExists) {
        alert('Este correo ya está registrado.');
        submitRegisterBtn.disabled = false;
        return;
      }

      // Hashing de contraseña (SHA256) antes de persistir
      const hashedPassword = hashPassword(password);

      registeredUsers.push({
        name: name,
        email: email,
        passwordHash: hashedPassword
      });
      localStorage.setItem('registered_users', JSON.stringify(registeredUsers));

      showToast('🎉 ¡Registro completado con éxito!');
      
      registerName.value = '';
      registerEmail.value = '';
      registerPassword.value = '';
      
      isPasswordValid = false;
      if (passwordStrengthWrapper) passwordStrengthWrapper.style.display = 'none';

      authRegisterForm.style.display = 'none';
      authLoginForm.style.display = 'flex';

      loginEmail.value = email;
      loginPassword.value = '';
      
      submitRegisterBtn.disabled = false;
    });
  }

  // --- 🔑 INICIO DE SESIÓN MULTI-USUARIO ---
  normalLoginBtn.addEventListener('click', () => {
    if (checkLockout()) return;

    const email = loginEmail.value.trim();
    const password = loginPassword.value.trim();

    let authenticatedUser = null;

    if (email.toLowerCase() === 'admin@alertavecinal.com' && password === 'admin123') {
      authenticatedUser = {
        name: 'Administrador',
        email: email,
        provider: 'credentials'
      };
    } else {
      let registeredUsers = [];
      try {
        registeredUsers = JSON.parse(localStorage.getItem('registered_users') || '[]');
        if (!Array.isArray(registeredUsers)) registeredUsers = [];
      } catch (err) {
        registeredUsers = [];
      }

      const user = registeredUsers.find(u => u.email.toLowerCase() === email.toLowerCase());
      
      if (user) {
        const inputPasswordHash = hashPassword(password);
        const fallbackHash = 'fb_' + btoa(unescape(encodeURIComponent(password)));
        if (user.passwordHash === inputPasswordHash || user.passwordHash === fallbackHash) {
          authenticatedUser = {
            name: user.name,
            email: user.email,
            provider: 'credentials'
          };
        }
      }
    }

    if (authenticatedUser) {
      authFailures = 0;
      localStorage.removeItem('auth_failures');
      localStorage.removeItem('lockout_timestamp');
      
      deriveSessionKey(password);

      logInSuccess(authenticatedUser);
    } else {
      authFailures++;
      localStorage.setItem('auth_failures', authFailures);
      
      if (authFailures >= 5) {
        lockoutTimestamp = Date.now();
        localStorage.setItem('lockout_timestamp', lockoutTimestamp);
        checkLockout();
        showToast('⚠️ Cuenta bloqueada temporalmente por exceso de intentos.');
      } else {
        alert(`Credenciales incorrectas. Intento ${authFailures} de 5.`);
      }
    }
  });

  googleLoginBtn.addEventListener('click', () => {
    if (CONFIG.GOOGLE_CLIENT_ID) {
      googleLoginBtn.textContent = 'Cargando Google...';
      googleLoginBtn.disabled = true;

      try {
        google.accounts.id.initialize({
          client_id: CONFIG.GOOGLE_CLIENT_ID,
          callback: handleGoogleCredentialResponse
        });
        
        google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            googleLoginBtn.textContent = 'Iniciar Sesión con Google';
            googleLoginBtn.disabled = false;
          }
        });
      } catch (err) {
        console.error("Error inicializando Google Identity Services:", err);
        showToast("⚠️ Falló conexión con Google OAuth. Usando mock configurado.");
        loginWithMockGoogle();
      }
    } else {
      loginWithMockGoogle();
    }
  });

  function loginWithMockGoogle() {
    googleLoginBtn.textContent = 'Autenticando...';
    googleLoginBtn.disabled = true;

    const mockUser = CONFIG.MOCK_GOOGLE_USER || { name: 'Usuario Demo', email: 'demo@example.com' };
    showToast(`🔄 Autenticando (modo local) como ${mockUser.name}...`);

    setTimeout(() => {
      googleLoginBtn.textContent = 'Iniciar Sesión con Google';
      googleLoginBtn.disabled = false;
      
      deriveSessionKey(`google_mock_${mockUser.email}`);

      logInSuccess({
        name: mockUser.name,
        email: mockUser.email,
        picture: '',
        provider: 'google'
      });
    }, 1000);
  }

  function handleGoogleCredentialResponse(response) {
    googleLoginBtn.textContent = 'Iniciar Sesión con Google';
    googleLoginBtn.disabled = false;

    try {
      const base64Url = response.credential.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));

      const payload = JSON.parse(jsonPayload);
      
      deriveSessionKey(payload.sub || payload.email);

      logInSuccess({
        name: payload.name,
        email: payload.email,
        picture: payload.picture || '',
        provider: 'google'
      });
    } catch (e) {
      console.error("Error decodificando token de Google:", e);
      showToast("❌ Error al autenticar con Google.");
    }
  }

  logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('user_session');
    sessionStorage.removeItem('session_crypto_key');
    sessionCryptoKey = null;
    isAdmin = false;
    
    // Ocultar panel de admin al cerrar sesion
    const adminPanel = document.getElementById('adminPanel');
    if (adminPanel) adminPanel.style.display = 'none';
    if (telegramAdminSection) telegramAdminSection.style.display = 'none';

    if (ws) ws.close();
    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);
    if (fixedLensInterval) clearInterval(fixedLensInterval);
    stopAlarmSound();
    
    appLayout.style.display = 'none';
    loginScreen.style.display = 'flex';
    showToast('🔒 Sesión cerrada correctamente.');
  });

  // --- VIEW TABS ROUTER ---
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      views.forEach(v => v.classList.remove('active'));

      btn.classList.add('active');
      const target = btn.getAttribute('data-target');
      document.getElementById(target).classList.add('active');
    });
  });

  // --- 🔊 AUDIO & MICROPHONE SIMULATION ---
  toolTalk.addEventListener('mousedown', startTalking);
  toolTalk.addEventListener('mouseup', stopTalking);
  toolTalk.addEventListener('mouseleave', stopTalking); // Parar si arrastra el mouse afuera
  
  // Soporte para pantallas táctiles móviles
  toolTalk.addEventListener('touchstart', (e) => {
    e.preventDefault();
    startTalking();
  });
  toolTalk.addEventListener('touchend', (e) => {
    e.preventDefault();
    stopTalking();
  });

  // --- 🎙️ AUDIO CAPTURE AND PLAYBACK HELPER FUNCTIONS ---
  let audioCtx = null;
  let nextAudioTime = 0;

  function playRawPcm(base64Data) {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 8000 });
        nextAudioTime = audioCtx.currentTime;
      }
      
      const binaryString = atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }
      
      const audioBuffer = audioCtx.createBuffer(1, float32Array.length, 8000);
      audioBuffer.copyToChannel(float32Array, 0);
      
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtx.destination);
      
      if (nextAudioTime < audioCtx.currentTime) {
        nextAudioTime = audioCtx.currentTime;
      }
      source.start(nextAudioTime);
      nextAudioTime += audioBuffer.duration;
    } catch (e) {
      console.error("Error al reproducir audio: ", e);
    }
  }

  let audioContextMic = null;
  let micSource = null;
  let processor = null;
  let micStream = null;

  async function startMicCapture() {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextMic = new (window.AudioContext || window.webkitAudioContext)();
      micSource = audioContextMic.createMediaStreamSource(micStream);
      
      processor = audioContextMic.createScriptProcessor(2048, 1, 1);
      
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        const targetSampleRate = 8000;
        const ratio = audioContextMic.sampleRate / targetSampleRate;
        const length = Math.round(inputData.length / ratio);
        const pcmData = new Int16Array(length);
        
        for (let i = 0; i < length; i++) {
          const idx = Math.round(i * ratio);
          const sample = Math.max(-1, Math.min(1, inputData[idx] || 0));
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        
        const binary = String.fromCharCode.apply(null, new Uint8Array(pcmData.buffer));
        const base64 = btoa(binary);
        
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            "cmd": "mic_audio",
            "data": base64
          }));
        }
      };
      
      micSource.connect(processor);
      processor.connect(audioContextMic.destination);
    } catch (err) {
      console.error("Error capturando micrófono:", err);
      showToast("⚠️ Permiso de micrófono denegado o no disponible.");
    }
  }

  function stopMicCapture() {
    try {
      if (processor) {
        processor.disconnect();
        processor = null;
      }
      if (micSource) {
        micSource.disconnect();
        micSource = null;
      }
      if (audioContextMic) {
        audioContextMic.close();
        audioContextMic = null;
      }
      if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
      }
    } catch (e) {
      console.error("Error deteniendo captura mic:", e);
    }
  }

  function startTalking() {
    if (!toolTalk.classList.contains('active')) {
      toolTalk.classList.add('active');
      showToast('🎤 Micrófono abierto. Transmitiendo voz a la bocina de la cámara...');
      startMicCapture();
    }
  }

  function stopTalking() {
    if (toolTalk.classList.contains('active')) {
      toolTalk.classList.remove('active');
      showToast('🎤 Micrófono cerrado.');
      stopMicCapture();
    }
  }

  toolListen.addEventListener('click', () => {
    toolListen.classList.toggle('active');
    const active = toolListen.classList.contains('active');
    showToast(active ? '🔊 Audio ambiental de la cámara activado.' : '🔇 Audio ambiental silenciado.');
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        "cmd": "audio_stream",
        "active": active
      }));
    }
  });

  // --- 📷 SNAPSHOT CAPTURE ---
  toolCapture.addEventListener('click', () => {
    // Animación visual de flash en la pantalla
    lensPtzContainer.style.filter = 'brightness(2) contrast(1.2)';
    setTimeout(() => {
      lensPtzContainer.style.filter = '';
    }, 150);

    // Convertir el canvas activo a imagen y forzar descarga
    try {
      const link = document.createElement('a');
      link.download = `AlertaVecinal_Captura_${Date.now()}.jpg`;
      link.href = videoCanvasPtz.toDataURL('image/jpeg', 0.85);
      link.click();
      showToast('📷 Captura de pantalla guardada en Descargas.');
    } catch (err) {
      console.error(err);
      showToast('❌ No se pudo guardar la captura (Sin origen de video activo).');
    }
  });

  // --- 🤖 AI TOGGLE CONTROL ---
  toolAi.addEventListener('click', () => {
    isAiActive = !isAiActive;
    
    if (isAiActive) {
      toolAi.classList.add('active');
      showToast('🤖 Procesamiento de IA para lectura de placas ACTIVADO.');
    } else {
      toolAi.classList.remove('active');
      showToast('🤖 Detección de placas DESACTIVADO. Ignorando escaneos.');
    }

    // Enviar comando al servidor real
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        "cmd": "toggle_ai",
        "active": isAiActive
      }));
    }
  });

  // --- 📷 CAMERA VIEW TABS (Grid / Gran Angular / PTZ) ---
  const camTabs = document.querySelectorAll('.cam-tab');
  const camViewPanes = document.querySelectorAll('.cam-view-pane');
  const gridSizeSelector = document.getElementById('gridSizeSelector');
  const camGridContainer = document.getElementById('camGridContainer');
  const auxCells = document.querySelectorAll('.aux-cell');

  function switchCameraTab(view) {
    camTabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
    camViewPanes.forEach(p => p.classList.remove('active'));

    const activeTab = document.querySelector(`.cam-tab[data-view="${view}"]`);
    if (activeTab) { activeTab.classList.add('active'); activeTab.setAttribute('aria-selected', 'true'); }

    const paneId = 'view' + view.charAt(0).toUpperCase() + view.slice(1);
    const targetPane = document.getElementById(paneId);
    if (targetPane) targetPane.classList.add('active');

    if (gridSizeSelector) {
      gridSizeSelector.style.display = (view === 'grid') ? 'flex' : 'none';
    }
  }

  camTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const view = tab.getAttribute('data-view');
      switchCameraTab(view);
      if (lensSelector) {
        if (view === 'fixed') lensSelector.value = 'fixed';
        else if (view === 'ptz') lensSelector.value = 'ptz';
      }
    });
  });

  // --- 📐 DYNAMIC GRID SIZE ---
  function applyGridLayout(mode) {
    if (!camGridContainer) return;
    auxCells.forEach(c => c.classList.add('hidden-cam'));
    const fixedEl = document.getElementById('lensFixedContainer');
    const ptzEl   = document.getElementById('lensPtzContainer');
    if (fixedEl) fixedEl.classList.remove('hidden-cam');
    if (ptzEl)   ptzEl.classList.remove('hidden-cam');

    if (mode === 'fixed' || mode === '1') {
      camGridContainer.setAttribute('data-grid', '1');
      if (ptzEl) ptzEl.classList.add('hidden-cam');
    } else if (mode === 'ptz') {
      camGridContainer.setAttribute('data-grid', '1');
      if (fixedEl) fixedEl.classList.add('hidden-cam');
    } else if (mode === '2') {
      camGridContainer.setAttribute('data-grid', '2');
    } else if (mode === '4') {
      camGridContainer.setAttribute('data-grid', '4');
      for (let i = 0; i < 2; i++) { if (auxCells[i]) auxCells[i].classList.remove('hidden-cam'); }
    } else if (mode === '9') {
      camGridContainer.setAttribute('data-grid', '9');
      for (let i = 0; i < 7; i++) { if (auxCells[i]) auxCells[i].classList.remove('hidden-cam'); }
    } else if (mode === '16') {
      camGridContainer.setAttribute('data-grid', '16');
      for (let i = 0; i < 14; i++) { if (auxCells[i]) auxCells[i].classList.remove('hidden-cam'); }
    }
  }

  // Init default: 2-camera grid
  applyGridLayout('2');

  // Wire selector
  if (lensSelector) {
    lensSelector.addEventListener('change', function() {
      const mode = this.value;
      if (mode === 'fixed') {
        switchCameraTab('fixed');
      } else if (mode === 'ptz') {
        switchCameraTab('ptz');
      } else {
        applyGridLayout(mode);
        switchCameraTab('grid');
      }
    });
  }

  // Legacy expand buttons → switch to single-view tabs
  if (toggleFixedBtn) { toggleFixedBtn.addEventListener('click', () => switchCameraTab('fixed')); }
  if (togglePtzBtn)   { togglePtzBtn.addEventListener('click',   () => switchCameraTab('ptz'));   }

  // --- 🔒 MOSTRAR/OCULTAR CONTRASEÑA ---
  if (showPasswordCheckbox) {
    showPasswordCheckbox.addEventListener('change', function() {
      loginPassword.type = this.checked ? 'text' : 'password';
    });
  }

  // --- 🕹️ PTZ JOYSTICK & ZOOM OVERLAYS ---
  ptzDirs.forEach(dirBtn => {
    dirBtn.addEventListener('click', () => {
      const direction = dirBtn.getAttribute('data-dir');
      if (!direction) return;

      // Efecto botón
      dirBtn.style.color = 'var(--primary-color)';
      setTimeout(() => dirBtn.style.color = '', 200);

      showToast(`🕹️ Moviendo cámara hacia: ${direction.toUpperCase()}`);

      // Enviar comando PTZ al servidor en modo real
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          "cmd": "ptz",
          "action": direction
        }));
      }

      // Desplazar coordenadas del radar en Modo Demo
      if (demoMode) {
        const step = 20;
        if (direction === 'up') ptzOffsetY -= step;
        if (direction === 'down') ptzOffsetY += step;
        if (direction === 'left') ptzOffsetX -= step;
        if (direction === 'right') ptzOffsetX += step;
      }
    });
  });

  if (ptzCenterBtn) {
    ptzCenterBtn.addEventListener('click', () => {
      showToast('🕹️ Cámara centrada.');
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ "cmd": "ptz", "action": "center" }));
      }
      if (demoMode) { ptzOffsetX = 0; ptzOffsetY = 0; demoZoomScale = 1.0; }
    });
  }

  zoomBtns.forEach(zBtn => {
    zBtn.addEventListener('click', () => {
      const zoomAction = zBtn.getAttribute('data-zoom');
      showToast(`🔍 Ajustando zoom: ZOOM ${zoomAction.toUpperCase()}`);

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          "cmd": "zoom",
          "action": zoomAction
        }));
      }

      if (demoMode) {
        if (zoomAction === 'in') demoZoomScale = Math.min(demoZoomScale + 0.2, 2.5);
        if (zoomAction === 'out') demoZoomScale = Math.max(demoZoomScale - 0.2, 0.6);
      }
    });
  }

  // --- 📷 LOCAL WEBCAM (1-CLICK GETUSERMEDIA) ---
  let localWebcamStream = null;
  let localWebcamVideoEl = null;
  let localWebcamAnimationFrame = null;
  let lastWebcamFrameSentTime = 0;

  if (useWebcamBtn) {
    useWebcamBtn.addEventListener('click', async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          showToast('❌ Tu navegador no soporta acceso directo a la webcam.');
          return;
        }

        useWebcamBtn.disabled = true;
        useWebcamBtn.textContent = '⏳ Accediendo a la cámara...';

        localWebcamStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
        });

        if (!localWebcamVideoEl) {
          localWebcamVideoEl = document.createElement('video');
          localWebcamVideoEl.autoplay = true;
          localWebcamVideoEl.playsInline = true;
          localWebcamVideoEl.muted = true;
        }
        localWebcamVideoEl.srcObject = localWebcamStream;
        await localWebcamVideoEl.play();

        const placeholderFixed = document.getElementById('placeholderFixed');
        const placeholderPtz = document.getElementById('placeholderPtz');
        if (placeholderFixed) placeholderFixed.style.display = 'none';
        if (placeholderPtz) placeholderPtz.style.display = 'none';

        if (activeCameraInfo) {
          activeCameraInfo.value = '📷 Cámara Web de este Dispositivo';
        }

        useWebcamBtn.disabled = false;
        useWebcamBtn.textContent = '✅ Cámara Web Activa (1-Clic)';
        showToast('📷 Cámara web de tu dispositivo conectada con éxito.');

        const renderLoop = () => {
          if (!localWebcamStream) return;
          const videoCanvasFixed = document.getElementById('videoCanvasFixed');
          const videoCanvasPtz = document.getElementById('videoCanvasPtz');

          if (videoCanvasFixed && localWebcamVideoEl.videoWidth) {
            const ctxFixed = videoCanvasFixed.getContext('2d');
            videoCanvasFixed.width = localWebcamVideoEl.videoWidth;
            videoCanvasFixed.height = localWebcamVideoEl.videoHeight;
            ctxFixed.drawImage(localWebcamVideoEl, 0, 0, videoCanvasFixed.width, videoCanvasFixed.height);
          }

          if (videoCanvasPtz && localWebcamVideoEl.videoWidth) {
            const ctxPtz = videoCanvasPtz.getContext('2d');
            videoCanvasPtz.width = localWebcamVideoEl.videoWidth;
            videoCanvasPtz.height = localWebcamVideoEl.videoHeight;
            ctxPtz.drawImage(localWebcamVideoEl, 0, 0, videoCanvasPtz.width, videoCanvasPtz.height);
          }

          const now = Date.now();
          if (ws && ws.readyState === WebSocket.OPEN && (now - lastWebcamFrameSentTime > 200)) {
            lastWebcamFrameSentTime = now;
            if (videoCanvasFixed) {
              const dataUrl = videoCanvasFixed.toDataURL('image/jpeg', 0.6);
              ws.send(JSON.stringify({
                cmd: 'process_frame',
                image: dataUrl
              }));
            }
          }

          localWebcamAnimationFrame = requestAnimationFrame(renderLoop);
        };

        if (localWebcamAnimationFrame) cancelAnimationFrame(localWebcamAnimationFrame);
        renderLoop();

      } catch (err) {
        console.error('Error al acceder a la webcam:', err);
        useWebcamBtn.disabled = false;
        useWebcamBtn.textContent = '📷 Usar Cámara de este Dispositivo (1-Clic)';
        showToast('❌ Permiso de cámara denegado o no disponible.');
      }
    });
  });

  // --- 📢 TEXT-TO-SPEECH (TTS) ALERTS ---
  function speakAlert(plate) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const spelledPlate = plate.split('').join(' ');
      const utterance = new SpeechSynthesisUtterance(`Alerta, placa ${spelledPlate} con reporte de robo detectada`);
      utterance.lang = 'es-ES';
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }
  }

  // --- 💾 TELEGRAM CONFIG SAVING ---
  if (saveTelegramBtn) {
    saveTelegramBtn.addEventListener('click', () => {
      const token = telegramTokenInput.value.trim();
      const chatId = telegramChatIdInput.value.trim();

      setLocalItem('telegram_token', token);
      setLocalItem('telegram_chat_id', chatId);

      showToast('💾 Configuración de Telegram guardada localmente.');
      
      // Enviar configuración al servidor si está conectado
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          "cmd": "save_telegram_config",
          "token": token,
          "chat_id": chatId
        }));
      }
    });
  }

  // --- 💬 TELEGRAM WIZARD HELPER ---
  function updateTelegramBotLink(username) {
    if (!telegramBotLink) return;
    telegramBotLink.style.display = 'flex';
    if (username) {
      telegramBotLink.href = `https://t.me/${username}`;
    }
  }

  // --- HISTORY MANAGEMENT ---
  function loadHistoryEncrypted() {
    try {
      const encryptedData = getLocalItem('alert_history');
      if (!encryptedData) return [];
      if (!sessionCryptoKey) {
        console.warn("Intento de leer el historial sin clave de sesión activa.");
        return [];
      }
      
      const bytes = CryptoJS.AES.decrypt(encryptedData, sessionCryptoKey);
      const decryptedText = bytes.toString(CryptoJS.enc.Utf8);
      if (!decryptedText) {
        console.warn("No se pudo descifrar el historial (llave incorrecta o corrupta).");
        return [];
      }
      return JSON.parse(decryptedText);
    } catch (e) {
      console.error("Error al descifrar el historial:", e);
      return [];
    }
  }

  function saveHistory() {
    if (!sessionCryptoKey) return;
    try {
      const plainText = JSON.stringify(history);
      const encryptedData = CryptoJS.AES.encrypt(plainText, sessionCryptoKey).toString();
      setLocalItem('alert_history', encryptedData);
    } catch (e) {
      console.error("Error al cifrar el historial:", e);
    }
  }

  function renderHistory() {
    historyTableBody.innerHTML = '';
    mobileHistoryList.innerHTML = '';

    const searchInput = document.getElementById('searchPlate');
    const filterInput = document.getElementById('filterStatus');
    const searchQuery = searchInput ? searchInput.value.trim().toUpperCase() : '';
    const filterValue = filterInput ? filterInput.value : 'all';

    const activeHistory = demoMode ? demoHistory : history;

    const filtered = activeHistory.filter(item => {
      const matchesSearch = (item.placa || '').toUpperCase().includes(searchQuery);
      let matchesFilter = true;
      if (filterValue === 'stolen') {
        matchesFilter = item.es_robado;
      } else if (filterValue === 'authorized') {
        matchesFilter = !item.es_robado;
      }
      return matchesSearch && matchesFilter;
    });

    if (filtered.length === 0) {
      const emptyRow = `<tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">No hay detecciones que coincidan</td></tr>`;
      historyTableBody.innerHTML = emptyRow;
      mobileHistoryList.innerHTML = `<div style="text-align:center; color: var(--text-secondary); padding: 20px;">No hay detecciones que coincidan</div>`;
      return;
    }

    filtered.forEach(item => {
      // 1. Desktop Table Row
      const tr = document.createElement('tr');
      if (item.es_robado) {
        tr.style.backgroundColor = 'rgba(255, 107, 107, 0.05)';
      }
      
      const statusText = item.es_robado ? '⚠️ ROBADO' : '✅ LIBRE';
      const statusColor = item.es_robado ? 'var(--alert-color)' : 'var(--success-color)';
      
      tr.innerHTML = `
        <td style="font-weight: 700; letter-spacing: 0.5px;">${item.placa}</td>
        <td style="font-weight: 700; color: ${statusColor}">${statusText}</td>
        <td>${item.modelo || '?'} (${item.color || '?'})</td>
        <td>${item.propietario || '?'}</td>
        <td>${item.timeStr || '?'}</td>
      `;
      historyTableBody.appendChild(tr);

      // 2. Mobile List Card
      const card = document.createElement('div');
      card.className = `history-card ${item.es_robado ? 'stolen' : 'normal'}`;
      card.innerHTML = `
        <div class="history-card-header">
          <span class="plate-badge">${item.placa}</span>
          <span class="status-badge ${item.es_robado ? 'stolen' : 'normal'}">${statusText}</span>
        </div>
        <div class="history-card-details">
          <div class="detail-item">
            <span>Vehículo</span>
            <p>${item.modelo || '?'} (${item.color || '?'})</p>
          </div>
          <div class="detail-item">
            <span>Propietario</span>
            <p>${item.propietario || '?'}</p>
          </div>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); text-align: right; margin-top: 4px;">
          ${item.timeStr || '?'}
        </div>
      `;
      mobileHistoryList.appendChild(card);
    });
  }

  function addAlert(alertData) {
    if (!isAiActive) return; // Si la IA está apagada en el control rápido, ignorar alertas.

    let timeStr = '';
    if (alertData.timestamp) {
      const dateObj = new Date(alertData.timestamp);
      timeStr = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + 
                dateObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
    } else {
      timeStr = new Date().toLocaleTimeString('es-ES');
    }

    const formattedAlert = {
      placa: alertData.placa || '?',
      es_robado: alertData.es_robado || false,
      modelo: alertData.modelo || '?',
      color: alertData.color || '?',
      propietario: alertData.propietario || '?',
      timestamp: alertData.timestamp || new Date().toISOString(),
      timeStr: timeStr
    };

    // Agregar al historial adecuado
    if (demoMode) {
      demoHistory.unshift(formattedAlert);
      if (demoHistory.length > 100) {
        demoHistory.pop();
      }
    } else {
      history.unshift(formattedAlert);
      if (history.length > 100) {
        history.pop();
      }
      saveHistory();
    }

    renderHistory();

    // Si es robado, disparar modal y TTS
    if (formattedAlert.es_robado) {
      showCriticalModal(formattedAlert);
    } else {
      showToast(`✅ Placa autorizada detectada: ${formattedAlert.placa}`);
    }
  }

  function mergeHistoryFromServer(serverAlerts) {
    if (!serverAlerts || !Array.isArray(serverAlerts)) return;
    
    serverAlerts.forEach(alert => {
      const exists = history.some(h => h.placa === alert.placa && h.timestamp === alert.timestamp);
      if (!exists) {
        const dateObj = new Date(alert.timestamp || Date.now());
        const timeStr = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) + ' ' + 
                        dateObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });

        history.push({
          placa: alert.placa || '?',
          es_robado: alert.es_robado || false,
          modelo: alert.modelo || '?',
          color: alert.color || '?',
          propietario: alert.propietario || '?',
          timestamp: alert.timestamp || new Date().toISOString(),
          timeStr: timeStr
        });
      }
    });

    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    if (history.length > 100) {
      history = history.slice(0, 100);
    }

    saveHistory();
    renderHistory();
  }

  // --- 🚨 SYNTHESIZED SIREN ALARM SOUND (Web Audio API) ---
  let alarmAudioCtx = null;
  let alarmOscillator1 = null;
  let alarmOscillator2 = null;
  let alarmGainNode = null;
  let alarmInterval = null;

  function playAlarmSound() {
    try {
      if (!alarmAudioCtx) {
        alarmAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (alarmAudioCtx.state === 'suspended') {
        alarmAudioCtx.resume();
      }
      if (alarmInterval) return;

      alarmGainNode = alarmAudioCtx.createGain();
      alarmGainNode.gain.setValueAtTime(0.2, alarmAudioCtx.currentTime);
      alarmGainNode.connect(alarmAudioCtx.destination);

      alarmOscillator1 = alarmAudioCtx.createOscillator();
      alarmOscillator1.type = 'sawtooth';
      alarmOscillator1.frequency.setValueAtTime(700, alarmAudioCtx.currentTime);
      alarmOscillator1.connect(alarmGainNode);
      alarmOscillator1.start();

      alarmOscillator2 = alarmAudioCtx.createOscillator();
      alarmOscillator2.type = 'sine';
      alarmOscillator2.frequency.setValueAtTime(2.5, alarmAudioCtx.currentTime);
      
      const lfoGain = alarmAudioCtx.createGain();
      lfoGain.gain.setValueAtTime(150, alarmAudioCtx.currentTime);
      
      alarmOscillator2.connect(lfoGain);
      lfoGain.connect(alarmOscillator1.frequency);
      alarmOscillator2.start();

      let alt = false;
      alarmInterval = setInterval(() => {
        if (alarmOscillator1 && alarmAudioCtx.state === 'running') {
          const nextFreq = alt ? 850 : 600;
          alarmOscillator1.frequency.linearRampToValueAtTime(nextFreq, alarmAudioCtx.currentTime + 0.35);
          alt = !alt;
        }
      }, 400);
    } catch (e) {
      console.error("No se pudo iniciar el sonido de alarma:", e);
    }
  }

  function stopAlarmSound() {
    if (alarmInterval) {
      clearInterval(alarmInterval);
      alarmInterval = null;
    }
    try {
      if (alarmOscillator1) {
        alarmOscillator1.stop();
        alarmOscillator1.disconnect();
        alarmOscillator1 = null;
      }
      if (alarmOscillator2) {
        alarmOscillator2.stop();
        alarmOscillator2.disconnect();
        alarmOscillator2 = null;
      }
      if (alarmGainNode) {
        alarmGainNode.disconnect();
        alarmGainNode = null;
      }
    } catch (e) {
      console.error("Error al detener la sirena:", e);
    }
  }

  // --- CRITICAL MODAL SCREEN ---
  function showCriticalModal(alertData) {
    criticalPlate.textContent = alertData.placa;
    criticalModel.textContent = alertData.modelo || '?';
    criticalColor.textContent = alertData.color || '?';
    criticalOwner.textContent = alertData.propietario || '?';
    criticalTime.textContent = alertData.timeStr || new Date().toLocaleTimeString();
    
    criticalAlertModal.classList.add('active');
    speakAlert(alertData.placa);

    // Respetar preferencias del usuario
    if (prefAlarmSound) playAlarmSound();
    if (prefVibration && navigator.vibrate) navigator.vibrate([400, 200, 400, 200, 800]);
    if (prefBrowserNotif && Notification.permission === 'granted') {
      new Notification('🚨 PLACA ROBADA DETECTADA', {
        body: `${alertData.placa} — ${alertData.modelo || '?'} (${alertData.color || '?'})`,
        icon: '/logo_project.png',
        badge: '/logo_project.png'
      });
    }
  }

  dismissAlertBtn.addEventListener('click', () => {
    criticalAlertModal.classList.remove('active');
    stopAlarmSound();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  });

  // --- 📷 FIXED LENS STATIC SECURITY OVERVIEW ---
  function startFixedLensRender() {
    if (fixedLensInterval) clearInterval(fixedLensInterval);
    
    videoCanvasFixed.width = 640;
    videoCanvasFixed.height = 360;
    placeholderFixed.style.display = 'none';

    fixedLensInterval = setInterval(() => {
      // 1. Dibujar fondo de calles/esquema
      ctxFixed.fillStyle = '#0F1626';
      ctxFixed.fillRect(0, 0, videoCanvasFixed.width, videoCanvasFixed.height);

      // 2. Líneas de calle
      ctxFixed.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      ctxFixed.lineWidth = 3;
      ctxFixed.beginPath();
      ctxFixed.moveTo(0, 240);
      ctxFixed.lineTo(videoCanvasFixed.width, 240);
      ctxFixed.stroke();

      ctxFixed.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctxFixed.setLineDash([12, 12]);
      ctxFixed.beginPath();
      ctxFixed.moveTo(0, 160);
      ctxFixed.lineTo(videoCanvasFixed.width, 160);
      ctxFixed.stroke();
      ctxFixed.setLineDash([]); // reset

      // 3. Edificios del esquema
      ctxFixed.fillStyle = '#1B2A4A';
      ctxFixed.fillRect(0, 0, 110, 140);
      ctxFixed.fillRect(530, 0, 110, 140);
      
      // Dibujar plantas/árboles esquemáticos
      ctxFixed.fillStyle = '#223B2F';
      ctxFixed.beginPath();
      ctxFixed.arc(50, 180, 20, 0, Math.PI * 2);
      ctxFixed.arc(590, 180, 20, 0, Math.PI * 2);
      ctxFixed.fill();

      // 4. Dibujar auto estático en el carril izquierdo
      ctxFixed.fillStyle = 'var(--text-secondary)';
      ctxFixed.fillRect(200, 180, 50, 30);
      ctxFixed.fillStyle = 'rgba(255,255,255,0.4)';
      ctxFixed.fillRect(210, 185, 10, 20); // Ventana

      // 5. Leyenda y Marca de agua
      ctxFixed.fillStyle = '#00C2D1';
      ctxFixed.font = '600 12px Outfit';
      ctxFixed.fillText('CÁMARA REJILLA - RESUMEN GENERAL (FIJO)', 20, 30);
      
      ctxFixed.fillStyle = 'rgba(255, 255, 255, 0.4)';
      ctxFixed.font = '500 11px Outfit';
      ctxFixed.fillText('CAM-LENTE-SUPERIOR | 30 FPS', 20, 48);

      // 6. Dot de grabación verde parpadeando
      if (Math.floor(Date.now() / 800) % 2 === 0) {
        ctxFixed.fillStyle = 'var(--success-color)';
        ctxFixed.beginPath();
        ctxFixed.arc(610, 25, 6, 0, Math.PI*2);
        ctxFixed.fill();
      }
    }, 1000 / 15);
  }

  // --- WEBSOCKET CONNECTION & MANAGEMENT ---
  function connectWebSocket() {
    if (demoMode) return;

    let ip = serverIpInput.value.trim() || '127.0.0.1';
    let port = serverPortInput.value.trim() || '8765';
    
    setLocalItem('server_ip', ip);
    setLocalItem('server_port', port);

    let wsUrl = '';
    
    // Autodetectar protocolo seguro si la página corre bajo HTTPS
    const isHttpsPage = window.location.protocol === 'https:';

    if (ip.startsWith('ws://') || ip.startsWith('wss://')) {
      wsUrl = ip;
      // Forzar wss sólo si la página web corre sobre HTTPS (exigido por seguridad del navegador)
      if (isHttpsPage && wsUrl.startsWith('ws://')) {
        wsUrl = wsUrl.replace(/^ws:\/\//, 'wss://');
      }
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else if (ip.startsWith('http://') || ip.startsWith('https://')) {
      wsUrl = ip.replace(/^http/, 'ws');
      if (isHttpsPage && wsUrl.startsWith('ws://')) {
        wsUrl = wsUrl.replace(/^ws:\/\//, 'wss://');
      }
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else {
      // Es una IP o un dominio sin protocolo
      let protocol = 'ws';
      const isLocal = ip === 'localhost' || ip === '127.0.0.1' || ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.');
      if (isHttpsPage || !isLocal) {
        protocol = 'wss';
      }
      
      const isDomain = ip.includes('.') && !/^[0-9.]+$/.test(ip) && ip !== 'localhost';
      
      if (isDomain && (port === '80' || port === '443' || port === '')) {
        wsUrl = `${protocol}://${ip}/ws`;
      } else {
        wsUrl = `${protocol}://${ip}:${port}/ws`;
      }
    }

    if (ws) ws.close();

    wsStatusText.textContent = t('status_connecting');
    wsStatusDot.className = 'dot connecting';
    connectBtn.textContent = t('status_connecting');
    
    videoSpinner.style.display = 'inline-block';
    ptzMsg.textContent = t('status_connecting_ia');
    placeholderPtz.style.display = 'flex';

    ws = new WebSocket(wsUrl);
    ws.binaryType = 'blob';

    ws.onopen = () => {
      console.log('WebSocket Conectado');
      wsStatusText.textContent = 'Conectado';
      wsStatusDot.className = 'dot connected';
      connectBtn.textContent = 'Desconectar';
      connectBtn.className = 'btn btn-alert';
      placeholderPtz.style.display = 'none';
      recIndicator.style.display = 'flex';
      
      // Sincronizar datos iniciales
      ws.send(JSON.stringify({ "cmd": "get_history", "limite_historial": 15 }));
      
      const token = telegramTokenInput ? telegramTokenInput.value.trim() : '';
      const chatId = telegramChatIdInput ? telegramChatIdInput.value.trim() : '';
      if (token && chatId) {
        ws.send(JSON.stringify({
          "cmd": "save_telegram_config",
          "token": token,
          "chat_id": chatId
        }));
      }
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'history') {
            mergeHistoryFromServer(data.alerts);
          } 
          else if (data.type === 'alert') {
            addAlert(data);
          } 
          else if (data.type === 'status') {
            if (data.camera) {
              activeCameraInfo.value = data.camera;
            }
            videoMetaText.textContent = t('cam_meta').replace('{fps}', data.fps || '0.0').replace('{clients}', data.clients || '0');
            if (data.bot_username) {
              updateTelegramBotLink(data.bot_username);
            }
          } 
          else if (data.type === 'cameras') {
            populateCamerasModal(data.list);
          }
          else if (data.type === 'frame_meta') {
            videoMetaText.textContent = t('cam_meta').replace('{fps}', data.fps || '0.0').replace('{clients}', data.clients || '0');
          }
          else if (data.type === 'audio') {
            playRawPcm(data.data);
          }
          else if (data.type === 'toast') {
            showToast(data.message);
          }
        } catch (err) {
          console.error(err);
        }
      } 
      else if (event.data instanceof Blob) {
        try {
          // Detener el loop de la simulación fija si empieza a llegar video real
          if (fixedLensInterval) {
            clearInterval(fixedLensInterval);
            fixedLensInterval = null;
          }

          const imageBitmap = await createImageBitmap(event.data);
          const w = imageBitmap.width;
          const h = imageBitmap.height;

          // Si la altura es mayor o igual a la anchura, es doble lente (dos frames de 16:9 apilados verticalmente)
          const isDualLens = (h / w) >= 1.0;

          if (isDualLens) {
            const halfHeight = h / 2;

            if (videoCanvasPtz.width !== w || videoCanvasPtz.height !== halfHeight) {
              videoCanvasPtz.width = w;
              videoCanvasPtz.height = halfHeight;
              videoCanvasFixed.width = w;
              videoCanvasFixed.height = halfHeight;
            }

            // Asegurar que el contenedor del lente fijo esté visible
            if (lensFixedContainer.classList.contains('collapsed')) {
              lensFixedContainer.classList.remove('collapsed');
            }
            ptzOverlay.style.display = 'flex'; // Mostrar pad de PTZ

            // Lente Superior (Fijo): Dibuja la mitad superior del frame de video
            ctxFixed.drawImage(imageBitmap, 
              0, 0, w, halfHeight, 
              0, 0, videoCanvasFixed.width, videoCanvasFixed.height
            );
            
            // Lente Inferior (PTZ): Dibuja la mitad inferior del frame de video
            ctxPtz.drawImage(imageBitmap, 
              0, halfHeight, w, halfHeight, 
              0, 0, videoCanvasPtz.width, videoCanvasPtz.height
            );
            placeholderFixed.style.display = 'none';
          } else {
            // Mapear pantalla simple (webcam, laptop camera, etc.)
            if (videoCanvasPtz.width !== w || videoCanvasPtz.height !== h) {
              videoCanvasPtz.width = w;
              videoCanvasPtz.height = h;
            }

            // Colapsar el lente fijo y ocultar los controles PTZ
            if (!lensFixedContainer.classList.contains('collapsed')) {
              lensFixedContainer.classList.add('collapsed');
            }
            ptzOverlay.style.display = 'none';

            // Dibujar el frame completo en el canvas principal (PTZ)
            ctxPtz.drawImage(imageBitmap, 
              0, 0, w, h, 
              0, 0, videoCanvasPtz.width, videoCanvasPtz.height
            );
          }

          placeholderPtz.style.display = 'none';
        } catch (err) {
          console.error(err);
        }
      }
    };

    ws.onclose = () => {
      wsStatusText.textContent = t('status_disconnected');
      wsStatusDot.className = 'dot';
      connectBtn.textContent = t('admin_connect');
      connectBtn.className = 'btn';
      recIndicator.style.display = 'none';
      placeholderPtz.style.display = 'flex';
      videoSpinner.style.display = 'none';

      // Detect Mixed Content Block (HTTPS website connecting to HTTP/WS local backend)
      const isHttps = window.location.protocol === 'https:';
      const isLocalIp = ip === 'localhost' || ip === '127.0.0.1' || ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.');

      if (isHttps && isLocalIp) {
        ptzMsg.innerHTML = `<span style="color:#FFD600; font-weight:bold; font-size:0.85rem;">${t('status_https_error_title')}</span><br>` +
                           `<span style="font-size:0.75rem; color:#fff; display:block; margin-top:5px; max-width:90%;">${t('status_https_error_desc')}</span><br>` +
                           `<span style="font-size:0.72rem; color:#aaa; display:block;"><b>${t('status_https_error_sol_title')}:</b> ${t('status_https_error_sol_desc')}<br><code style="color:#FFD600; background:rgba(0,0,0,0.5); padding:2px 4px; border-radius:3px;">python -m http.server 8000</code> y entra a: <br><a href="http://localhost:8000/web_pwa/" target="_blank" style="color:#00C2D1; text-decoration:underline;">http://localhost:8000/web_pwa/</a></span>`;
      } else {
        ptzMsg.textContent = t('status_server_disconnected');
      }
      
      // Reiniciar la simulación del lente fijo al desconectarse del backend
      startFixedLensRender();
      placeholderFixed.style.display = 'flex';
      
      if (!userDisconnected) {
        scheduleReconnect();
      }
    };

    ws.onerror = (err) => {
      console.error(err);
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    if (demoMode || userDisconnected) return;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    
    wsStatusText.textContent = t('status_reconnecting');
    wsStatusDot.className = 'dot connecting';
    
    reconnectTimeout = setTimeout(() => {
      connectWebSocket();
    }, 3000);
  }

  connectBtn.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      userDisconnected = true;
      ws.close();
    } else {
      userDisconnected = false;
      connectWebSocket();
    }
  });

  applyRtspBtn.addEventListener('click', () => {
    const url = rtspUrlInput.value.trim();
    if (!url) return;
    
    if (demoMode) {
      activeCameraInfo.value = `[DEMO] ${url}`;
      showToast('📡 Ruta de cámara demo aplicada.');
      return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        "cmd": "change_camera_url",
        "url": url
      }));
      showToast('📡 Enviando cambio de cámara RTSP...');
    } else {
      showToast('⚠️ Servidor desconectado. Revisa la configuración de IP/Puerto.', 'warning');
      console.warn('Para conectar un backend local (ws://) desde HTTPS (Vercel), debes usar un túnel seguro (localtunnel) o correr la app en local (http://localhost:8000).');
    }
  });

  listCamerasBtn.addEventListener('click', () => {
    if (demoMode) {
      populateCamerasModal(['📹 Lente Gran Angular Integrado', 'Lente Especial PTZ 4K']);
      return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ "cmd": "list_cameras" }));
    } else {
      showToast('⚠️ Conéctate al servidor primero.', 'warning');
    }
  });

  function populateCamerasModal(camerasList) {
    cameraListContainer.innerHTML = '';
    
    if (!camerasList || camerasList.length === 0) {
      cameraListContainer.innerHTML = `<p style="color:var(--text-secondary); text-align:center;">No se detectaron lentes adicionales.</p>`;
    } else {
      camerasList.forEach((cam, index) => {
        const btn = document.createElement('button');
        btn.className = 'camera-option-btn';
        btn.textContent = cam;
        btn.addEventListener('click', () => {
          if (demoMode) {
            activeCameraInfo.value = cam;
          } else if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              "cmd": "change_camera",
              "index": index
            }));
            activeCameraInfo.value = cam;
          }
          cameraSelectModal.classList.remove('active');
          showToast(`📹 Lente principal asignado a: ${cam}`);
        });
        cameraListContainer.appendChild(btn);
      });
    }

    cameraSelectModal.classList.add('active');
  }

  closeCameraModalBtn.addEventListener('click', () => {
    cameraSelectModal.classList.remove('active');
  });

  // --- DEMO MODE MODULE (OFFLINE INTERACTIVO) ---
  function startDemoMode() {
    demoMode = true;
    demoBadge.style.display = 'inline-block';
    triggerDemoAlertBtn.style.display = 'inline-block';
    
    wsStatusText.textContent = `${t('status_connected')} (Demo)`;
    wsStatusDot.className = 'dot connected';
    placeholderPtz.style.display = 'none';
    recIndicator.style.display = 'flex';
    
    const demoModeBadge = document.getElementById('demoModeBadge');
    if (demoModeBadge) {
      demoModeBadge.textContent = t('admin_demo_active');
      demoModeBadge.className = 'status-badge-active';
    }

    if (ws) ws.close();
    
    demoHistory = [];
    preloadDemoHistory();

    startDemoCanvasAnimation();
    startDemoAlertGenerator();
    showToast(t('toast_demo_started'));
  }

  function stopDemoMode() {
    demoMode = false;
    demoBadge.style.display = 'none';
    triggerDemoAlertBtn.style.display = 'none';

    wsStatusText.textContent = t('status_disconnected');
    wsStatusDot.className = 'dot';
    recIndicator.style.display = 'none';
    placeholderPtz.style.display = 'flex';

    const demoModeBadge = document.getElementById('demoModeBadge');
    if (demoModeBadge) {
      demoModeBadge.textContent = t('admin_demo_inactive');
      demoModeBadge.className = 'status-badge-inactive';
    }
    showToast(t('toast_demo_stopped'));

    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);

    userDisconnected = false;
    demoHistory = [];
    renderHistory();
    connectWebSocket();
    showToast('🔌 Modo Demo apagado. Intentando conectar al servidor backend.');
  }

  function startDemoCanvasAnimation() {
    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    
    let angle = 0;
    videoCanvasPtz.width = 640;
    videoCanvasPtz.height = 360;

    demoCanvasInterval = setInterval(() => {
      ctxPtz.fillStyle = '#0E121A'; 
      ctxPtz.fillRect(0, 0, videoCanvasPtz.width, videoCanvasPtz.height);

      ctxPtz.save();
      
      // Aplicar desplazamiento PTZ y Escala de Zoom
      ctxPtz.translate(videoCanvasPtz.width / 2, videoCanvasPtz.height / 2);
      ctxPtz.scale(demoZoomScale, demoZoomScale);
      ctxPtz.translate(-videoCanvasPtz.width / 2 + ptzOffsetX, -videoCanvasPtz.height / 2 + ptzOffsetY);

      // Dibujar cuadrícula de radar
      ctxPtz.strokeStyle = 'rgba(0, 194, 209, 0.12)';
      ctxPtz.lineWidth = 1;
      const gridSize = 40;
      for (let x = -200; x < videoCanvasPtz.width + 200; x += gridSize) {
        ctxPtz.beginPath();
        ctxPtz.moveTo(x, -200);
        ctxPtz.lineTo(x, videoCanvasPtz.height + 200);
        ctxPtz.stroke();
      }
      for (let y = -200; y < videoCanvasPtz.height + 200; y += gridSize) {
        ctxPtz.beginPath();
        ctxPtz.moveTo(-200, y);
        ctxPtz.lineTo(videoCanvasPtz.width + 200, y);
        ctxPtz.stroke();
      }

      // Línea de barrido de radar
      ctxPtz.strokeStyle = 'rgba(0, 194, 209, 0.35)';
      ctxPtz.lineWidth = 2.5;
      ctxPtz.beginPath();
      let scanX = (angle % (videoCanvasPtz.width + 200)) - 100;
      ctxPtz.moveTo(scanX, -100);
      ctxPtz.lineTo(scanX, videoCanvasPtz.height + 100);
      ctxPtz.stroke();

      // Degradado del barrido
      let gradient = ctxPtz.createLinearGradient(scanX - 120, 0, scanX, 0);
      gradient.addColorStop(0, 'rgba(0, 194, 209, 0)');
      gradient.addColorStop(1, 'rgba(0, 194, 209, 0.15)');
      ctxPtz.fillStyle = gradient;
      ctxPtz.fillRect(scanX - 120, -100, 120, videoCanvasPtz.height + 200);

      // Dibujar auto simulado 1
      ctxPtz.strokeStyle = 'var(--primary-color)';
      ctxPtz.lineWidth = 2;
      ctxPtz.strokeRect(120, 120, 130, 80);
      ctxPtz.fillStyle = 'var(--primary-color)';
      ctxPtz.font = '12px Outfit';
      ctxPtz.fillText('Vehículo [ID: 72] 96%', 120, 112);

      // Si hay alerta activa demo
      if (Date.now() - lastDemoAlertTime < 5000) {
        ctxPtz.strokeStyle = 'var(--alert-color)';
        ctxPtz.lineWidth = 3;
        ctxPtz.strokeRect(320, 150, 160, 90);
        ctxPtz.fillStyle = 'var(--alert-color)';
        ctxPtz.font = '700 13px Outfit';
        ctxPtz.fillText('⚠️ PLACA ROBADA: ' + lastDemoPlate, 320, 140);
      }

      ctxPtz.restore();

      // Texto de información fija
      ctxPtz.fillStyle = '#F8F9FA';
      ctxPtz.font = '600 12px Outfit';
      ctxPtz.fillText('MONITOR LENTE MÓVIL (PTZ)', 20, 30);
      
      ctxPtz.fillStyle = 'rgba(255,255,255,0.5)';
      ctxPtz.font = '500 11px Outfit';
      ctxPtz.fillText(`PTZ Offset: X:${ptzOffsetX} Y:${ptzOffsetY} | Zoom: ${demoZoomScale.toFixed(1)}x`, 20, 48);

      angle += 6;
    }, 1000 / 30);
  }

  function startDemoAlertGenerator() {
    if (demoAlertInterval) clearInterval(demoAlertInterval);
    demoAlertInterval = setInterval(triggerDemoAlert, 15000);
  }

  function triggerDemoAlert() {
    const mockPlacas = [
      { placa: "JVM-892", es_robado: true, modelo: "Toyota Corolla", color: "Gris", propietario: "Carlos Gómez" },
      { placa: "KLO-112", es_robado: false, modelo: "Honda Civic", color: "Negro", propietario: "Sofía Méndez" },
      { placa: "XRT-403", es_robado: true, modelo: "Ford Mustang", color: "Rojo", propietario: "María Rodríguez" },
      { placa: "ZXC-883", es_robado: false, modelo: "Mazda 3", color: "Gris", propietario: "Roberto Díaz" },
      { placa: "YTR-442", es_robado: true, modelo: "Nissan Tsuru", color: "Rojo", propietario: "Griselda Ruiz" },
      { placa: "PLM-112", es_robado: false, modelo: "Hyundai Accent", color: "Azul", propietario: "Diego López" }
    ];

    const mock = mockPlacas[demoPlateIndex % mockPlacas.length];
    demoPlateIndex++;

    const alertData = {
      placa: mock.placa,
      es_robado: mock.es_robado,
      modelo: mock.modelo,
      color: mock.color,
      propietario: mock.propietario,
      timestamp: new Date().toISOString()
    };

    lastDemoPlate = mock.placa;
    lastDemoAlertTime = Date.now();

    addAlert(alertData);
  }

  function preloadDemoHistory() {
    const demoAlerts = [
      { placa: "MHX-901", es_robado: true, modelo: "Chevrolet Aveo", color: "Negro", propietario: "Luis Torres", timestamp: new Date(Date.now() - 3600000 * 2).toISOString() },
      { placa: "KLP-204", es_robado: false, modelo: "Volkswagen Jetta", color: "Blanco", propietario: "Ana Martínez", timestamp: new Date(Date.now() - 3600000 * 1.5).toISOString() },
      { placa: "YTR-442", es_robado: true, modelo: "Nissan Tsuru", color: "Rojo", propietario: "Griselda Ruiz", timestamp: new Date(Date.now() - 3600000 * 1.2).toISOString() },
      { placa: "ZXC-883", es_robado: false, modelo: "Mazda 3", color: "Gris", propietario: "Roberto Díaz", timestamp: new Date(Date.now() - 3600000 * 0.8).toISOString() },
      { placa: "PLM-112", es_robado: false, modelo: "Hyundai Accent", color: "Azul", propietario: "Sofía Méndez", timestamp: new Date(Date.now() - 3600000 * 0.2).toISOString() }
    ];

    demoAlerts.forEach(alert => {
      const exists = demoHistory.some(h => h.placa === alert.placa);
      if (!exists) {
        const dateObj = new Date(alert.timestamp);
        const timeStr = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) + ' ' + 
                        dateObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        
        demoHistory.push({
          ...alert,
          timeStr: timeStr
        });
      }
    });

    demoHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    renderHistory();
  }

  // --- ACTIONS & BINDINGS ---
  demoModeToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
      startDemoMode();
    } else {
      stopDemoMode();
    }
  });

  triggerDemoAlertBtn.addEventListener('click', triggerDemoAlert);

  clearHistoryBtn.addEventListener('click', () => {
    if (confirm('¿Deseas vaciar el historial de alertas local?')) {
      if (demoMode) {
        demoHistory = [];
      } else {
        history = [];
        saveHistory();
      }
      renderHistory();
      showToast('🗑️ Historial vaciado.');
    }
  });

  // --- LÓGICA DE LA GUÍA DE USUARIO (ONBOARDING) ---
  function showGuideSlide(index) {
    if (!guideSlides || guideSlides.length === 0) return;
    
    guideSlides.forEach((slide, idx) => {
      slide.classList.toggle('active', idx === index);
    });
    
    guideDots.forEach((dot, idx) => {
      dot.classList.toggle('active', idx === index);
    });
    
    currentGuideSlide = index;

    // Controlar visibilidad del botón anterior
    if (index === 0) {
      if (prevGuideBtn) prevGuideBtn.style.visibility = 'hidden';
    } else {
      if (prevGuideBtn) prevGuideBtn.style.visibility = 'visible';
    }

    // Cambiar texto de botón siguiente en la última slide
    if (nextGuideBtn) {
      if (index === guideSlides.length - 1) {
        nextGuideBtn.textContent = '¡Entendido!';
      } else {
        nextGuideBtn.textContent = 'Siguiente';
      }
    }
  }

  function nextGuideSlide() {
    if (currentGuideSlide < guideSlides.length - 1) {
      showGuideSlide(currentGuideSlide + 1);
    } else {
      closeUserGuide();
    }
  }

  function prevGuideSlide() {
    if (currentGuideSlide > 0) {
      showGuideSlide(currentGuideSlide - 1);
    }
  }

  function closeUserGuide() {
    if (userGuideModal) {
      userGuideModal.classList.remove('active');
    }
    setLocalItem('user_guide_seen', 'true');
    showToast('📖 Guía finalizada. Puedes volver a abrirla presionando 📖 en la cabecera.');
  }

  function openUserGuide() {
    showGuideSlide(0);
    if (userGuideModal) {
      userGuideModal.classList.add('active');
    }
  }

  // Event Listeners de la Guía
  if (userGuideBtn) {
    userGuideBtn.addEventListener('click', openUserGuide);
  }
  if (closeGuideBtn) {
    closeGuideBtn.addEventListener('click', () => {
      if (userGuideModal) {
        userGuideModal.classList.remove('active');
      }
      setLocalItem('user_guide_seen', 'true');
    });
  }
  if (nextGuideBtn) {
    nextGuideBtn.addEventListener('click', nextGuideSlide);
  }
  if (prevGuideBtn) {
    prevGuideBtn.addEventListener('click', prevGuideSlide);
  }
  if (guideDots) {
    guideDots.forEach(dot => {
      dot.addEventListener('click', () => {
        const targetIndex = parseInt(dot.getAttribute('data-goto'));
        if (!isNaN(targetIndex)) {
          showGuideSlide(targetIndex);
        }
      });
    });
  }

  // --- MANUAL THEME SELECTION LOGIC ---
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const savedTheme = getLocalItem('theme', '');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
  
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon(currentTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      setLocalItem('theme', currentTheme);
      updateThemeIcon(currentTheme);
      showToast(`🌓 Modo ${currentTheme === 'dark' ? 'oscuro' : 'claro'} activado`);
    });
  }

  function updateThemeIcon(theme) {
    if (!themeToggleBtn) return;
    themeToggleBtn.textContent = (theme === 'dark') ? '☀️' : '🌙';
  }

  // --- ⚙️ USER PREFERENCES SYSTEM ---
  function saveUserPreference(key, value) {
    setLocalItem(`pref_${key}`, String(value));
  }

  function loadUserPreferences() {
    const boolVal = (key, def) => {
      const v = getLocalItem(`pref_${key}`);
      return v === '' ? def : v === 'true';
    };
    const strVal = (key, def) => getLocalItem(`pref_${key}`) || def;
    const numVal = (key, def) => parseInt(getLocalItem(`pref_${key}`)) || def;

    prefAlarmSound    = boolVal('alarmSound', true);
    prefBrowserNotif  = boolVal('browserNotif', false);
    prefVibration     = boolVal('vibration', true);
    prefShowFps       = boolVal('showFps', true);
    prefFilterStolen  = boolVal('filterStolen', false);
    prefStartView     = strVal('startView', 'view-monitor');
    prefTimeFormat    = strVal('timeFormat', '24');
    prefLanguage      = strVal('language', 'es');
    prefTimezone      = strVal('timezone', 'America/Mexico_City');
    prefMaxHistory    = numVal('maxHistory', 100);
    prefFontSize      = numVal('fontSize', 14);
  }

  function applyUserPreferences() {
    // Sincronizar checkboxes
    const s = (id, val) => { const el = document.getElementById(id); if (el) el.checked = val; };
    const sv = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };

    s('settingAlarmSound',   prefAlarmSound);
    s('settingBrowserNotif', prefBrowserNotif);
    s('settingVibration',    prefVibration);
    s('settingShowFps',      prefShowFps);
    s('settingFilterStolen', prefFilterStolen);
    sv('settingTheme',       currentTheme);
    sv('settingStartView',   prefStartView);
    sv('settingMaxHistory',  prefMaxHistory);
    sv('settingTimeFormat',  prefTimeFormat);
    sv('settingLanguage',    prefLanguage);
    sv('settingTimezone',    prefTimezone);
    sv('settingFontSize',    prefFontSize);

    // Actualizar label del slider
    const lbl = document.getElementById('settingFontSizeLabel');
    if (lbl) lbl.textContent = `${prefFontSize}px`;

    // Aplicar tamaño de fuente
    document.documentElement.style.fontSize = `${prefFontSize}px`;

    // Aplicar visibilidad de FPS
    const fpsEl = document.getElementById('videoMetaText');
    if (fpsEl) fpsEl.style.display = prefShowFps ? '' : 'none';

    // Aplicar filtro por defecto en historial
    const filterSel = document.getElementById('filterStatus');
    if (filterSel && prefFilterStolen) filterSel.value = 'stolen';

    // Navegar a la vista predeterminada
    const defaultTab = document.querySelector(`.tab-btn[data-target="${prefStartView}"]`);
    if (defaultTab) defaultTab.click();

    // Aplicar idioma guardado (después del login, cuando el DOM ya está listo)
    if (prefLanguage && prefLanguage !== 'es') {
      setTimeout(() => applyLanguage(prefLanguage), 100);
    }
  }

  function wireUserPreferencesListeners() {
    const onToggle = (id, key, prefVar, callback) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('change', () => {
        const val = el.checked;
        window[prefVar] = val; // actualizar var global no es posible directo, usamos closure
        saveUserPreference(key, val);
        if (callback) callback(val);
      });
    };
    const onSelect = (id, key, callback) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('change', () => {
        saveUserPreference(key, el.value);
        if (callback) callback(el.value);
      });
    };

    // Sonido
    const alarmEl = document.getElementById('settingAlarmSound');
    if (alarmEl) alarmEl.addEventListener('change', () => {
      prefAlarmSound = alarmEl.checked;
      saveUserPreference('alarmSound', prefAlarmSound);
      showToast(prefAlarmSound ? '🔔 Sonido de alertas activado' : '🔕 Sonido de alertas desactivado');
    });

    // Notificaciones del navegador
    const notifEl = document.getElementById('settingBrowserNotif');
    if (notifEl) notifEl.addEventListener('change', () => {
      if (notifEl.checked) {
        Notification.requestPermission().then(perm => {
          prefBrowserNotif = perm === 'granted';
          notifEl.checked = prefBrowserNotif;
          saveUserPreference('browserNotif', prefBrowserNotif);
          showToast(prefBrowserNotif ? '🔔 Notificaciones activadas' : '❌ Permiso denegado por el navegador');
        });
      } else {
        prefBrowserNotif = false;
        saveUserPreference('browserNotif', false);
        showToast('🔕 Notificaciones del navegador desactivadas');
      }
    });

    // Vibración
    const vibEl = document.getElementById('settingVibration');
    if (vibEl) vibEl.addEventListener('change', () => {
      prefVibration = vibEl.checked;
      saveUserPreference('vibration', prefVibration);
      if (prefVibration && navigator.vibrate) navigator.vibrate(200);
      showToast(prefVibration ? '📳 Vibración activada' : '📴 Vibración desactivada');
    });

    // Tema (sincronizado con el botón de la cabecera)
    const themeEl = document.getElementById('settingTheme');
    if (themeEl) themeEl.addEventListener('change', () => {
      currentTheme = themeEl.value;
      document.documentElement.setAttribute('data-theme', currentTheme);
      setLocalItem('theme', currentTheme);
      updateThemeIcon(currentTheme);
      showToast(`🌓 Tema ${currentTheme === 'dark' ? 'oscuro' : 'claro'} aplicado`);
    });

    // Vista predeterminada
    const startViewEl = document.getElementById('settingStartView');
    if (startViewEl) startViewEl.addEventListener('change', () => {
      prefStartView = startViewEl.value;
      saveUserPreference('startView', prefStartView);
      showToast('📍 Vista predeterminada guardada');
    });

    // FPS
    const fpsEl2 = document.getElementById('settingShowFps');
    if (fpsEl2) fpsEl2.addEventListener('change', () => {
      prefShowFps = fpsEl2.checked;
      saveUserPreference('showFps', prefShowFps);
      const metaEl = document.getElementById('videoMetaText');
      if (metaEl) metaEl.style.display = prefShowFps ? '' : 'none';
      showToast(prefShowFps ? '📊 Métricas FPS visibles' : '📊 Métricas FPS ocultas');
    });

    // Máximo historial
    const maxHEl = document.getElementById('settingMaxHistory');
    if (maxHEl) maxHEl.addEventListener('change', () => {
      prefMaxHistory = parseInt(maxHEl.value);
      saveUserPreference('maxHistory', prefMaxHistory);
      showToast(`📊 Límite de historial: ${prefMaxHistory} registros`);
    });

    // Formato de hora
    const timeFormatEl = document.getElementById('settingTimeFormat');
    if (timeFormatEl) timeFormatEl.addEventListener('change', () => {
      prefTimeFormat = timeFormatEl.value;
      saveUserPreference('timeFormat', prefTimeFormat);
      renderHistory();
      showToast(`⏰ Formato de hora: ${prefTimeFormat === '24' ? '24 horas' : '12 horas (AM/PM)'}`);
    });

    // Filtro por defecto
    const filterStolenEl = document.getElementById('settingFilterStolen');
    if (filterStolenEl) filterStolenEl.addEventListener('change', () => {
      prefFilterStolen = filterStolenEl.checked;
      saveUserPreference('filterStolen', prefFilterStolen);
      const filterSel = document.getElementById('filterStatus');
      if (filterSel) filterSel.value = prefFilterStolen ? 'stolen' : 'all';
      renderHistory();
      showToast(prefFilterStolen ? '🔴 Mostrando solo robados por defecto' : '🟢 Mostrando todos los vehículos por defecto');
    });

    // Idioma
    const langEl = document.getElementById('settingLanguage');
    if (langEl) langEl.addEventListener('change', () => {
      prefLanguage = langEl.value;
      saveUserPreference('language', prefLanguage);
      applyLanguage(prefLanguage);
      showToast(prefLanguage === 'en' ? '🇺🇸 Language: English' : '🇲🇽 Idioma: Español (México)');
    });

    // Zona horaria
    const tzEl = document.getElementById('settingTimezone');
    if (tzEl) tzEl.addEventListener('change', () => {
      prefTimezone = tzEl.value;
      saveUserPreference('timezone', prefTimezone);
      renderHistory();
      showToast(prefLanguage === 'en' ? '🌎 Time zone updated' : '🌎 Zona horaria actualizada');
    });

    // Tamaño de fuente
    const fontEl = document.getElementById('settingFontSize');
    const fontLbl = document.getElementById('settingFontSizeLabel');
    if (fontEl) fontEl.addEventListener('input', () => {
      prefFontSize = parseInt(fontEl.value);
      if (fontLbl) fontLbl.textContent = `${prefFontSize}px`;
      document.documentElement.style.fontSize = `${prefFontSize}px`;
    });
    if (fontEl) fontEl.addEventListener('change', () => {
      saveUserPreference('fontSize', prefFontSize);
      showToast(prefLanguage === 'en' ? `🔤 Text size: ${prefFontSize}px` : `🔤 Tamaño de texto: ${prefFontSize}px`);
    });
  }

  // ============================================================
  //  🌍 SISTEMA DE INTERNACIONALIZACIÓN (i18n)
  // ============================================================
  const translations = {
    es: {
      // Nav
      nav_monitor: 'Monitor', nav_history: 'Historial', nav_settings: 'Ajustes',
      // Status
      status_disconnected: 'Desconectado', status_reconnecting: 'Reconectando...',
      status_connected: 'Conectado', status_connecting: 'Conectando...',
      // Monitor tools
      tool_talk: 'Hablar', tool_listen: 'Escuchar', tool_capture: 'Captura', tool_ai: 'IA Placas',
      // Camera card
      cam_view_title: 'Visualización de Cámaras',
      cam_grid: 'Vista Rejilla', cam_wide: 'Gran Angular', cam_ptz: 'Lente PTZ',
      cam_layout: 'Diseño:',
      cam_config: 'Configuración de Cámara',
      cam_scan: '🔍 Escanear Cámaras USB',
      cam_rtsp: 'Cambiar dirección RTSP / Cámara WiFi:',
      cam_apply: 'Aplicar',
      cam_source: 'Origen de Video Actual:',
      cam_inactive: 'Cámara inactiva — Esperando señal',
      cam_select_usb: 'Seleccionar Cámara USB:',
      cam_layout_2: '2 Cámaras (1+1)',
      cam_layout_fixed: '1 Lente (Solo Fijo)',
      cam_layout_ptz: '1 Lente (Solo PTZ)',
      cam_layout_4: '4 Cámaras (2x2)',
      cam_layout_9: '9 Cámaras (3x3)',
      cam_layout_16: '16 Cámaras (4x4)',
      cam_source_none: 'Ninguna cámara activa',
      cam_inactive_aux: 'Cámara inactiva<br>Esperando señal',
      status_connecting_ia: 'Conectando al servidor IA...',
      status_server_disconnected: 'Servidor desconectado.',
      status_https_error_title: '⚠️ Error de Conexión (Bloqueo HTTPS)',
      status_https_error_desc: 'No se puede conectar a un servidor local ("localhost" o IP privada) desde una web segura (Vercel).',
      status_https_error_sol_title: 'Solución rápida',
      status_https_error_sol_desc: 'Corre la web en tu laptop ejecutando:',
      cam_fixed_name: 'Lente Gran Angular',
      cam_ptz_name: 'Lente Móvil',
      cam_fixed_fullscreen: 'Lente Gran Angular (Fijo) — Vista Completa',
      cam_ptz_fullscreen: 'Lente Móvil PTZ — Vista Completa',
      cam_aux_name: 'Cámara Auxiliar',
      cam_meta: 'FPS de Servidor: {fps} | Clientes: {clients}',
      toast_demo_started: '🚀 Modo Demo iniciado. Puedes usar los joysticks e interruptores.',
      toast_demo_stopped: '⏹️ Modo Demo detenido.',
      // History
      hist_title: 'Historial de Alertas',
      hist_export: '📥 Exportar CSV', hist_clear: '🗑️ Vaciar Logs',
      hist_search: 'Buscar por placa...',
      hist_all: 'Todos los vehículos', hist_stolen: 'Solo robados', hist_auth: 'Solo autorizados',
      hist_col_plate: 'Placa', hist_col_status: 'Estado',
      hist_col_model: 'Modelo y Color', hist_col_owner: 'Propietario', hist_col_date: 'Fecha y Hora',
      hist_no_records: 'Sin registros',
      hist_row_stolen: '🔴 ROBADO', hist_row_authorized: '🟢 Autorizado',
      // Settings - admin
      admin_backend: 'Conexión Servidor Backend',
      admin_ip: '🌐 Dirección IP del Servidor:', admin_port: '🔌 Puerto WebSocket:',
      admin_connect: 'Conectar',
      admin_demo: 'Módulo de Demostración (Offline)',
      admin_demo_label: 'Modo Demo', admin_demo_inactive: 'Inactivo', admin_demo_active: 'Activo',
      admin_demo_desc: 'Simular flujo completo con radar y alertas ficticias',
      admin_simulate: '🚨 Simular Alerta Crítica',
      // Settings - notifications
      pref_notif_title: '🔔 Notificaciones y Alertas',
      pref_alarm_title: 'Sonido de alerta crítica',
      pref_alarm_desc: 'Reproducir sirena al detectar un vehículo robado',
      pref_browser_title: 'Notificaciones del navegador',
      pref_browser_desc: 'Recibir alertas aunque la app esté en segundo plano',
      pref_vib_title: 'Vibración en alertas', pref_vib_mobile: '(móvil)',
      pref_vib_desc: 'Vibrar el dispositivo al recibir una alerta crítica',
      // Settings - appearance
      pref_appear_title: '🎨 Apariencia y Visualización',
      pref_theme_label: 'Tema visual:',
      pref_theme_dark: '🌙 Oscuro (Dark Mode)', pref_theme_light: '☀️ Claro (Light Mode)',
      pref_start_label: 'Vista al iniciar sesión:',
      pref_start_monitor: '📺 Monitor (por defecto)',
      pref_start_history: '📋 Historial de Alertas', pref_start_settings: '⚙️ Ajustes',
      pref_fps_title: 'Mostrar métricas técnicas (FPS)',
      pref_fps_desc: 'Ver FPS del servidor y número de clientes conectados',
      // Settings - history data
      pref_hist_title: '📋 Historial y Datos',
      pref_maxhist_label: 'Máximo de registros en historial:',
      pref_rec_50: '50 registros', pref_rec_100: '100 registros (recomendado)',
      pref_rec_200: '200 registros', pref_rec_500: '500 registros',
      pref_timefmt_label: 'Formato de hora en el historial:',
      pref_time24: '⏰ 24 horas (ej: 13:45)', pref_time12: '🕐 12 horas (ej: 1:45 PM)',
      pref_filter_title: 'Filtrar solo robados por defecto',
      pref_filter_desc: 'Al abrir el historial, mostrar solo vehículos con reporte de robo',
      // Settings - region
      pref_region_title: '🌍 Región, Idioma y Accesibilidad',
      pref_lang_label: 'Idioma de la interfaz:',
      pref_tz_label: 'Zona horaria para registros:',
      pref_font_label: 'Tamaño del texto de la interfaz:',
      // Profile
      profile_title: 'Perfil de Usuario (Google)',
      role_operator: 'Operador Vecinal', role_admin: 'Administrador 🔐',
      btn_logout: 'Cerrar Sesión',
      // Auth
      auth_subtitle: 'Plataforma de Monitoreo Inteligente',
      auth_email: 'Usuario / Correo:', auth_password: 'Contraseña:',
      auth_show_pw: 'Mostrar contraseña',
      auth_login: 'Iniciar Sesión', auth_google: 'Iniciar Sesión con Google',
      auth_first_time: '¿Primera vez en la plataforma?',
      auth_create: 'Crea tu cuenta de vecino',
      auth_have_account: '¿Ya tienes una cuenta registrada?',
      auth_go_login: 'Iniciar Sesión',
      auth_name: 'Nombre Completo:',
      auth_register: 'Registrarse',
      // Toasts
      toast_alarm_on: '🔔 Sonido de alertas activado',
      toast_alarm_off: '🔕 Sonido de alertas desactivado',
      toast_notif_on: '🔔 Notificaciones activadas',
      toast_notif_denied: '❌ Permiso denegado por el navegador',
      toast_notif_off: '🔕 Notificaciones del navegador desactivadas',
      toast_vib_on: '📳 Vibración activada', toast_vib_off: '📴 Vibración desactivada',
      toast_fps_on: '📊 Métricas FPS visibles', toast_fps_off: '📊 Métricas FPS ocultas',
      toast_start_view: '📍 Vista predeterminada guardada',
      toast_filter_stolen: '🔴 Mostrando solo robados por defecto',
      toast_filter_all: '🟢 Mostrando todos los vehículos por defecto',
      toast_tz: '🌎 Zona horaria actualizada',
      toast_welcome: '👋 ¡Bienvenido de nuevo',
      toast_logout: '🔒 Sesión cerrada correctamente.',
      toast_dark: '🌓 Modo oscuro activado', toast_light: '🌓 Modo claro activado',
      // Critical alert modal
      modal_title: 'ALERTA DE ROBO',
      modal_desc: 'Se ha detectado una coincidencia en la Base de Datos',
      modal_model: 'Modelo', modal_color: 'Color',
      modal_owner: 'Propietario', modal_time: 'Fecha / Hora',
      modal_dismiss: 'Entendido',
      // Telegram Card i18n
      tg_title: '🔔 Alertas de Telegram (Celular)',
      tg_desc: 'Recibe notificaciones automáticas con fotos del vehículo y de la placa directamente en tu celular.',
      tg_how: '¿Cómo activarlo?',
      tg_step1: 'Haz clic en el botón de abajo para abrir el bot en Telegram.',
      tg_step2: 'Presiona el botón de <strong>Iniciar</strong> o envía <strong>/start</strong>.',
      tg_step3: '¡Eso es todo! El sistema te registrará y recibirás alertas.',
      tg_btn: '💬 Abrir Bot de Telegram',
      tg_missing: '⚠️ El bot de Telegram no está configurado por el administrador aún.',
      tg_admin_title: 'Configuración del Bot de la Comunidad',
      tg_admin_token: 'Token del Bot (de @BotFather):',
      tg_admin_chatid: 'ID de Chat del Administrador:',
      tg_admin_btn: 'Guardar Credenciales del Bot',
    },

    en: {
      // Nav
      nav_monitor: 'Monitor', nav_history: 'History', nav_settings: 'Settings',
      // Status
      status_disconnected: 'Disconnected', status_reconnecting: 'Reconnecting...',
      status_connected: 'Connected', status_connecting: 'Connecting...',
      // Monitor tools
      tool_talk: 'Talk', tool_listen: 'Listen', tool_capture: 'Capture', tool_ai: 'AI Plates',
      // Camera card
      cam_view_title: 'Camera View',
      cam_grid: 'Grid View', cam_wide: 'Wide Angle', cam_ptz: 'PTZ Lens',
      cam_layout: 'Layout:',
      cam_config: 'Camera Configuration',
      cam_scan: '🔍 Scan USB Cameras',
      cam_rtsp: 'Change RTSP / WiFi Camera address:',
      cam_apply: 'Apply',
      cam_source: 'Current Video Source:',
      cam_inactive: 'Camera inactive — Awaiting signal',
      cam_select_usb: 'Select USB Camera:',
      cam_layout_2: '2 Cameras (1+1)',
      cam_layout_fixed: '1 Lens (Fixed Only)',
      cam_layout_ptz: '1 Lens (PTZ Only)',
      cam_layout_4: '4 Cameras (2x2)',
      cam_layout_9: '9 Cameras (3x3)',
      cam_layout_16: '16 Cameras (4x4)',
      cam_source_none: 'No active camera',
      cam_inactive_aux: 'Camera inactive<br>Awaiting signal',
      status_connecting_ia: 'Connecting to AI server...',
      status_server_disconnected: 'Server disconnected.',
      status_https_error_title: '⚠️ Connection Error (HTTPS Block)',
      status_https_error_desc: 'Cannot connect to a local server ("localhost" or private IP) from a secure website (Vercel).',
      status_https_error_sol_title: 'Quick solution',
      status_https_error_sol_desc: 'Run the web on your laptop executing:',
      cam_fixed_name: 'Wide Angle Lens',
      cam_ptz_name: 'Mobile Lens',
      cam_fixed_fullscreen: 'Wide Angle Lens (Fixed) — Full View',
      cam_ptz_fullscreen: 'Mobile PTZ Lens — Full View',
      cam_aux_name: 'Auxiliary Camera',
      cam_meta: 'Server FPS: {fps} | Clients: {clients}',
      toast_demo_started: '🚀 Demo Mode started. You can use the joysticks and switches.',
      toast_demo_stopped: '⏹️ Demo Mode stopped.',
      // History
      hist_title: 'Alert History',
      hist_export: '📥 Export CSV', hist_clear: '🗑️ Clear Logs',
      hist_search: 'Search by plate...',
      hist_all: 'All vehicles', hist_stolen: 'Stolen only', hist_auth: 'Authorized only',
      hist_col_plate: 'Plate', hist_col_status: 'Status',
      hist_col_model: 'Model & Color', hist_col_owner: 'Owner', hist_col_date: 'Date & Time',
      hist_no_records: 'No records',
      hist_row_stolen: '🔴 STOLEN', hist_row_authorized: '🟢 Authorized',
      // Settings - admin
      admin_backend: 'Backend Server Connection',
      admin_ip: '🌐 Server IP Address:', admin_port: '🔌 WebSocket Port:',
      admin_connect: 'Connect',
      admin_demo: 'Demo Module (Offline)',
      admin_demo_label: 'Demo Mode', admin_demo_inactive: 'Inactive', admin_demo_active: 'Active',
      admin_demo_desc: 'Simulate full flow with radar and fictitious alerts',
      admin_simulate: '🚨 Simulate Critical Alert',
      // Settings - notifications
      pref_notif_title: '🔔 Notifications & Alerts',
      pref_alarm_title: 'Critical alert sound',
      pref_alarm_desc: 'Play siren when a stolen vehicle is detected',
      pref_browser_title: 'Browser notifications',
      pref_browser_desc: 'Receive alerts even when the app is in the background',
      pref_vib_title: 'Vibration on alerts', pref_vib_mobile: '(mobile)',
      pref_vib_desc: 'Vibrate the device when a critical alert is received',
      // Settings - appearance
      pref_appear_title: '🎨 Appearance & Display',
      pref_theme_label: 'Visual theme:',
      pref_theme_dark: '🌙 Dark Mode', pref_theme_light: '☀️ Light Mode',
      pref_start_label: 'Default view on login:',
      pref_start_monitor: '📺 Monitor (default)',
      pref_start_history: '📋 Alert History', pref_start_settings: '⚙️ Settings',
      pref_fps_title: 'Show technical metrics (FPS)',
      pref_fps_desc: 'See server FPS and number of connected clients',
      // Settings - history data
      pref_hist_title: '📋 History & Data',
      pref_maxhist_label: 'Maximum history entries:',
      pref_rec_50: '50 records', pref_rec_100: '100 records (recommended)',
      pref_rec_200: '200 records', pref_rec_500: '500 records',
      pref_timefmt_label: 'Time format in history:',
      pref_time24: '⏰ 24 hours (e.g. 13:45)', pref_time12: '🕐 12 hours (e.g. 1:45 PM)',
      pref_filter_title: 'Filter only stolen by default',
      pref_filter_desc: 'When opening history, show only vehicles with theft report',
      // Settings - region
      pref_region_title: '🌍 Region, Language & Accessibility',
      pref_lang_label: 'Interface language:',
      pref_tz_label: 'Time zone for records:',
      pref_font_label: 'Interface text size:',
      // Profile
      profile_title: 'User Profile (Google)',
      role_operator: 'Neighborhood Operator', role_admin: 'Administrator 🔐',
      btn_logout: 'Sign Out',
      // Auth
      auth_subtitle: 'Intelligent Monitoring Platform',
      auth_email: 'Username / Email:', auth_password: 'Password:',
      auth_show_pw: 'Show password',
      auth_login: 'Sign In', auth_google: 'Sign In with Google',
      auth_first_time: 'First time on the platform?',
      auth_create: 'Create your neighborhood account',
      auth_have_account: 'Already have an account?',
      auth_go_login: 'Sign In',
      auth_name: 'Full Name:',
      auth_register: 'Register',
      // Toasts
      toast_alarm_on: '🔔 Alert sound enabled',
      toast_alarm_off: '🔕 Alert sound disabled',
      toast_notif_on: '🔔 Notifications enabled',
      toast_notif_denied: '❌ Permission denied by browser',
      toast_notif_off: '🔕 Browser notifications disabled',
      toast_vib_on: '📳 Vibration enabled', toast_vib_off: '📴 Vibration disabled',
      toast_fps_on: '📊 FPS metrics visible', toast_fps_off: '📊 FPS metrics hidden',
      toast_start_view: '📍 Default view saved',
      toast_filter_stolen: '🔴 Showing only stolen by default',
      toast_filter_all: '🟢 Showing all vehicles by default',
      toast_tz: '🌎 Time zone updated',
      toast_welcome: '👋 Welcome back',
      toast_logout: '🔒 Session closed successfully.',
      toast_dark: '🌓 Dark mode activated', toast_light: '🌓 Light mode activated',
      // Critical alert modal
      modal_title: 'THEFT ALERT',
      modal_desc: 'A match has been detected in the Database',
      modal_model: 'Model', modal_color: 'Color',
      modal_owner: 'Owner', modal_time: 'Date / Time',
      modal_dismiss: 'Understood',
      // Telegram Card i18n
      tg_title: '🔔 Telegram Alerts (Mobile)',
      tg_desc: 'Receive automatic notifications with photos of the vehicle and plate directly on your phone.',
      tg_how: 'How to activate?',
      tg_step1: 'Click the button below to open the bot on Telegram.',
      tg_step2: 'Press the <strong>Start</strong> button or send <strong>/start</strong>.',
      tg_step3: "That's it! The system will register you and you will receive alerts.",
      tg_btn: '💬 Open Telegram Bot',
      tg_missing: '⚠️ The Telegram bot is not configured by the administrator yet.',
      tg_admin_title: 'Community Bot Configuration',
      tg_admin_token: 'Bot Token (from @BotFather):',
      tg_admin_chatid: 'Administrator Chat ID:',
      tg_admin_btn: 'Save Bot Credentials',
    }
  };

  /** Traduce una clave al idioma actual */
  function t(key) {
    const lang = prefLanguage || 'es';
    return (translations[lang] && translations[lang][key]) ||
           (translations['es'] && translations['es'][key]) || key;
  }

  /** Aplica el idioma seleccionado a todos los elementos del DOM */
  function applyLanguage(lang) {
    prefLanguage = lang;
    const L = translations[lang] || translations['es'];

    // === NAVEGACIÓN ===
    document.querySelectorAll('.tab-btn').forEach(btn => {
      const target = btn.getAttribute('data-target');
      const icon = btn.querySelector('[aria-hidden="true"]');
      if (!icon) return;
      if (target === 'view-monitor') btn.lastChild.textContent = ' ' + L.nav_monitor;
      if (target === 'view-history') btn.lastChild.textContent = ' ' + L.nav_history;
      if (target === 'view-settings') btn.lastChild.textContent = ' ' + L.nav_settings;
    });

    // === BOTONES DE HERRAMIENTAS DEL MONITOR ===
    const toolMap = { toolTalk: 'tool_talk', toolListen: 'tool_listen', toolCapture: 'tool_capture', toolAi: 'tool_ai' };
    Object.entries(toolMap).forEach(([id, key]) => {
      const btn = document.getElementById(id);
      if (btn) { const sp = btn.querySelector('span:not(.tool-icon)'); if (sp) sp.textContent = L[key]; }
    });

    // === PANEL DE CÁMARA ===
    const camTitle = document.querySelector('.cam-panel-title');
    if (camTitle) camTitle.textContent = L.cam_view_title;

    const camTabs = document.querySelectorAll('.cam-tab');
    if (camTabs[0]) camTabs[0].lastChild.textContent = '\n                  ' + L.cam_grid + '\n                ';
    if (camTabs[1]) camTabs[1].lastChild.textContent = '\n                  ' + L.cam_wide + '\n                ';
    if (camTabs[2]) camTabs[2].lastChild.textContent = '\n                  ' + L.cam_ptz + '\n                ';

    const applyRtspBtn = document.getElementById('applyRtspBtn');
    if (applyRtspBtn) applyRtspBtn.textContent = L.cam_apply;

    const scanBtn = document.getElementById('listCamerasBtn');
    if (scanBtn) scanBtn.textContent = L.cam_scan;

    const rtspLabel = document.getElementById('label-rtsp-url');
    if (rtspLabel) rtspLabel.textContent = L.cam_rtsp;

    const camConfigH2 = document.querySelector('#view-monitor .monitor-grid > .card:last-child h2');
    if (camConfigH2) camConfigH2.textContent = L.cam_config;

    const usbLabel = document.getElementById('label-list-cameras');
    if (usbLabel) usbLabel.textContent = L.cam_select_usb;

    const activeCamLabel = document.getElementById('label-active-camera');
    if (activeCamLabel) activeCamLabel.textContent = L.cam_source;

    const lensLabel = document.getElementById('label-lens-selector');
    if (lensLabel) lensLabel.textContent = L.cam_layout;

    const lensSel = document.getElementById('lensSelector');
    if (lensSel && lensSel.options.length >= 6) {
      lensSel.options[0].text = L.cam_layout_2;
      lensSel.options[1].text = L.cam_layout_fixed;
      lensSel.options[2].text = L.cam_layout_ptz;
      lensSel.options[3].text = L.cam_layout_4;
      lensSel.options[4].text = L.cam_layout_9;
      lensSel.options[5].text = L.cam_layout_16;
    }

    if (activeCameraInfo) {
      if (activeCameraInfo.value === 'Ninguna cámara activa' || activeCameraInfo.value === 'No active camera') {
        activeCameraInfo.value = L.cam_source_none;
      }
    }

    const fixedMsg = document.getElementById('fixedMsg');
    if (fixedMsg) fixedMsg.textContent = L.cam_inactive;

    const ptzMsgEl = document.getElementById('ptzMsg');
    if (ptzMsgEl) {
      const txt = ptzMsgEl.textContent;
      if (txt === 'Cámara inactiva — Esperando señal' || txt === 'Camera inactive — Awaiting signal') {
        ptzMsgEl.textContent = L.cam_inactive;
      } else if (txt === 'Servidor desconectado.' || txt === 'Server disconnected.') {
        ptzMsgEl.textContent = L.status_server_disconnected;
      } else if (txt === 'Conectando al servidor IA...' || txt === 'Connecting to AI server...') {
        ptzMsgEl.textContent = L.status_connecting_ia;
      }
    }

    document.querySelectorAll('.aux-cell .cam-inactive-overlay span').forEach(el => {
      el.innerHTML = L.cam_inactive_aux;
    });

    // Translate Camera Names
    const fixedLbl = document.querySelector('#lensFixedContainer .cam-cell-name');
    if (fixedLbl) fixedLbl.textContent = L.cam_fixed_name;

    const ptzLbl = document.querySelector('#lensPtzContainer .cam-cell-name');
    if (ptzLbl) ptzLbl.textContent = L.cam_ptz_name;

    const fixedFsLbl = document.querySelector('#viewFixed .cam-cell-name');
    if (fixedFsLbl) fixedFsLbl.textContent = L.cam_fixed_fullscreen;

    const ptzFsLbl = document.querySelector('#viewPtz .cam-cell-name');
    if (ptzFsLbl) ptzFsLbl.textContent = L.cam_ptz_fullscreen;

    document.querySelectorAll('.aux-cell').forEach(cell => {
      const nameEl = cell.querySelector('.cam-cell-name');
      if (nameEl) {
        const num = cell.id.replace('auxCam', '');
        nameEl.textContent = `${L.cam_aux_name} ${parseInt(num) + 1}`;
      }
    });

    // === SECCIÓN HISTORIAL ===
    const histH2 = document.querySelector('#view-history h2');
    if (histH2) histH2.textContent = L.hist_title;

    const exportBtn = document.getElementById('exportCsvBtn');
    if (exportBtn) exportBtn.textContent = L.hist_export;

    const clearBtn = document.getElementById('clearHistoryBtn');
    if (clearBtn) clearBtn.textContent = L.hist_clear;

    const searchInput = document.getElementById('searchPlate');
    if (searchInput) searchInput.placeholder = L.hist_search;

    const filterSel = document.getElementById('filterStatus');
    if (filterSel && filterSel.options.length >= 3) {
      filterSel.options[0].text = L.hist_all;
      filterSel.options[1].text = L.hist_stolen;
      filterSel.options[2].text = L.hist_auth;
    }

    const ths = document.querySelectorAll('.history-table thead th');
    if (ths.length >= 5) {
      ths[0].textContent = L.hist_col_plate;
      ths[1].textContent = L.hist_col_status;
      ths[2].textContent = L.hist_col_model;
      ths[3].textContent = L.hist_col_owner;
      ths[4].textContent = L.hist_col_date;
    }

    // Re-renderizar historial para aplicar los textos de estado
    renderHistory();

    // === PANEL DE AJUSTES - TARJETAS DE USUARIO ===
    const cards = document.querySelectorAll('#userSettingsPanel .card');
    if (cards.length >= 4) {
      // Card 1: Notificaciones
      const c1 = cards[0];
      c1.querySelector('h2').textContent = L.pref_notif_title;
      const tw1 = c1.querySelectorAll('.toggle-wrapper');
      if (tw1[0]) { tw1[0].querySelector('h3').textContent = L.pref_alarm_title; tw1[0].querySelector('p').textContent = L.pref_alarm_desc; }
      if (tw1[1]) { tw1[1].querySelector('h3').textContent = L.pref_browser_title; tw1[1].querySelector('p').textContent = L.pref_browser_desc; }
      if (tw1[2]) {
        tw1[2].querySelector('h3').innerHTML = `${L.pref_vib_title} <span style="font-size:0.75rem;color:var(--text-secondary);">${L.pref_vib_mobile}</span>`;
        tw1[2].querySelector('p').textContent = L.pref_vib_desc;
      }

      // Card 2: Apariencia
      const c2 = cards[1];
      c2.querySelector('h2').textContent = L.pref_appear_title;
      const l2 = c2.querySelectorAll('label');
      if (l2[0]) l2[0].textContent = L.pref_theme_label;
      if (l2[1]) l2[1].textContent = L.pref_start_label;
      const thSel = document.getElementById('settingTheme');
      if (thSel) { thSel.options[0].text = L.pref_theme_dark; thSel.options[1].text = L.pref_theme_light; }
      const svSel = document.getElementById('settingStartView');
      if (svSel) { svSel.options[0].text = L.pref_start_monitor; svSel.options[1].text = L.pref_start_history; svSel.options[2].text = L.pref_start_settings; }
      const tw2 = c2.querySelector('.toggle-wrapper');
      if (tw2) { tw2.querySelector('h3').textContent = L.pref_fps_title; tw2.querySelector('p').textContent = L.pref_fps_desc; }

      // Card 3: Historial y Datos
      const c3 = cards[2];
      c3.querySelector('h2').textContent = L.pref_hist_title;
      const l3 = c3.querySelectorAll('label');
      if (l3[0]) l3[0].textContent = L.pref_maxhist_label;
      if (l3[1]) l3[1].textContent = L.pref_timefmt_label;
      const mhSel = document.getElementById('settingMaxHistory');
      if (mhSel) { mhSel.options[0].text = L.pref_rec_50; mhSel.options[1].text = L.pref_rec_100; mhSel.options[2].text = L.pref_rec_200; mhSel.options[3].text = L.pref_rec_500; }
      const tfSel = document.getElementById('settingTimeFormat');
      if (tfSel) { tfSel.options[0].text = L.pref_time24; tfSel.options[1].text = L.pref_time12; }
      const tw3 = c3.querySelector('.toggle-wrapper');
      if (tw3) { tw3.querySelector('h3').textContent = L.pref_filter_title; tw3.querySelector('p').textContent = L.pref_filter_desc; }

      // Card 4: Región, Idioma y Accesibilidad
      const c4 = cards[3];
      c4.querySelector('h2').textContent = L.pref_region_title;
      const l4 = c4.querySelectorAll('label');
      if (l4[0]) l4[0].textContent = L.pref_lang_label;
      if (l4[1]) l4[1].textContent = L.pref_tz_label;
      if (l4[2]) l4[2].textContent = L.pref_font_label;
    }

    // === CARD 5: TELEGRAM CONFIG ===
    const tgCard = document.getElementById('telegramConfigCard');
    if (tgCard) {
      const h2 = tgCard.querySelector('h2');
      if (h2) h2.textContent = L.tg_title;
      
      const descP = tgCard.querySelector('#telegramUserSection p');
      if (descP) descP.textContent = L.tg_desc;
      
      const howH4 = tgCard.querySelector('#telegramUserSection h4');
      if (howH4) howH4.textContent = L.tg_how;
      
      const steps = tgCard.querySelectorAll('#telegramUserSection ol li');
      if (steps.length >= 3) {
        steps[0].innerHTML = L.tg_step1;
        steps[1].innerHTML = L.tg_step2;
        steps[2].innerHTML = L.tg_step3;
      }
      
      const botLink = document.getElementById('telegramBotLink');
      if (botLink) {
        botLink.innerHTML = `💬 ${L.tg_btn.replace('💬 ', '')}`;
      }
    }

    // === PANEL ADMIN ===
    const backendCard = document.querySelector('#adminPanel .card');
    if (backendCard) {
      const h2 = backendCard.querySelector('h2');
      if (h2) h2.textContent = L.admin_backend;
      const connectBtnEl = document.getElementById('connectBtn');
      if (connectBtnEl && connectBtnEl.textContent !== 'Conectando...' && connectBtnEl.textContent !== 'Connecting...') {
        connectBtnEl.textContent = L.admin_connect;
      }
    }

    // === MÓDULO DE DEMOSTRACIÓN ===
    const demoCard = document.getElementById('demoModeCard');
    if (demoCard) {
      const h2 = demoCard.querySelector('h2');
      if (h2) h2.textContent = L.admin_demo;
      const demoP = demoCard.querySelector('.toggle-wrapper p');
      if (demoP) demoP.textContent = L.admin_demo_desc;
      const simBtn = document.getElementById('triggerDemoAlertBtn');
      if (simBtn) simBtn.textContent = L.admin_simulate;
      const demoToggleH3 = demoCard.querySelector('.toggle-wrapper h3');
      if (demoToggleH3) {
        demoToggleH3.innerHTML = `${L.admin_demo_label} <span id="demoModeBadge" class="${demoMode ? 'status-badge-active' : 'status-badge-inactive'}">${demoMode ? L.admin_demo_active : L.admin_demo_inactive}</span>`;
      }
    }

    // === PERFIL DE USUARIO ===
    const profileCard = document.getElementById('googleProfileCard');
    if (profileCard) {
      const ph2 = profileCard.querySelector('h2');
      if (ph2) ph2.textContent = L.profile_title;
      const logoutBtnEl = document.getElementById('logoutBtn');
      if (logoutBtnEl) logoutBtnEl.textContent = L.btn_logout;
      // Badge de rol
      const roleBadge = document.getElementById('userRoleBadge');
      if (roleBadge) roleBadge.textContent = isAdmin ? L.role_admin : L.role_operator;
    }

    // === FORMULARIO DE LOGIN ===
    const loginSubtitle = document.querySelector('.auth-header p');
    if (loginSubtitle) loginSubtitle.textContent = L.auth_subtitle;
    const emailLbl = document.querySelector('label[for="loginEmail"]');
    if (emailLbl) emailLbl.textContent = L.auth_email;
    const passLbl = document.querySelector('label[for="loginPassword"]');
    if (passLbl) passLbl.textContent = L.auth_password;
    const showPwLbl = document.querySelector('label[for="showPasswordCheckbox"]');
    if (showPwLbl) showPwLbl.textContent = L.auth_show_pw;
    const loginBtnEl = document.getElementById('normalLoginBtn');
    if (loginBtnEl) loginBtnEl.textContent = L.auth_login;
    const gLoginBtn = document.getElementById('googleLoginBtn');
    if (gLoginBtn) { const sp = gLoginBtn.querySelector('span'); if (sp) sp.textContent = L.auth_google; }
    const nameLbl = document.querySelector('label[for="registerName"]');
    if (nameLbl) nameLbl.textContent = L.auth_name;
    const regBtn = document.getElementById('submitRegisterBtn');
    if (regBtn) regBtn.textContent = L.auth_register;

    // === MODAL DE ALERTA CRÍTICA ===
    const modalTitle = document.getElementById('criticalAlertTitle');
    if (modalTitle) modalTitle.textContent = L.modal_title;
    const modalDesc = document.getElementById('criticalAlertDesc');
    if (modalDesc) modalDesc.textContent = L.modal_desc;
    const dismissBtn = document.getElementById('dismissAlertBtn');
    if (dismissBtn) dismissBtn.textContent = L.modal_dismiss;
    const modalLabels = document.querySelectorAll('.critical-details-grid label');
    if (modalLabels.length >= 4) {
      modalLabels[0].textContent = L.modal_model;
      modalLabels[1].textContent = L.modal_color;
      modalLabels[2].textContent = L.modal_owner;
      modalLabels[3].textContent = L.modal_time;
    }

    // === STATUS DEL WEBSOCKET ===
    const wsText = document.getElementById('wsStatusText');
    if (wsText) {
      const currentText = wsText.textContent;
      if (currentText === translations['es'].status_disconnected || currentText === translations['en'].status_disconnected)
        wsText.textContent = L.status_disconnected;
      else if (currentText === translations['es'].status_connected || currentText === translations['en'].status_connected)
        wsText.textContent = L.status_connected;
      else if (currentText === translations['es'].status_reconnecting || currentText === translations['en'].status_reconnecting)
        wsText.textContent = L.status_reconnecting;
    }

    // Actualizar selector de idioma en la opción inglés
    const langSelect = document.getElementById('settingLanguage');
    if (langSelect && langSelect.options.length >= 2) {
      langSelect.options[0].text = lang === 'en' ? '🇲🇽 Español (México)' : '🇲🇽 Español (México)';
      langSelect.options[1].text = lang === 'en' ? '🇺🇸 English' : '🇺🇸 English';
    }
  }

  // --- HISTORY SEARCH & FILTER LISTENERS ---
  const searchPlateInput = document.getElementById('searchPlate');
  const filterStatusSelect = document.getElementById('filterStatus');

  if (searchPlateInput) {
    searchPlateInput.addEventListener('input', renderHistory);
  }
  if (filterStatusSelect) {
    filterStatusSelect.addEventListener('change', renderHistory);
  }

  // --- EXPORT TO CSV LOGIC ---
  const exportCsvBtn = document.getElementById('exportCsvBtn');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      const activeHistory = demoMode ? demoHistory : history;
      if (activeHistory.length === 0) {
        alert('No hay registros en el historial para exportar.');
        return;
      }

      let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // UTF-8 BOM for Excel
      csvContent += "Placa,Estado,Modelo y Color,Propietario,Fecha y Hora\n";

      activeHistory.forEach(item => {
        const placa = (item.placa || '').replace(/"/g, '""');
        const estado = item.es_robado ? 'ROBADO' : 'LIBRE';
        const vehiculo = `${item.modelo || '?'} (${item.color || '?'})`.replace(/"/g, '""');
        const propietario = (item.propietario || '?').replace(/"/g, '""');
        const fecha = (item.timeStr || '?').replace(/"/g, '""');

        csvContent += `"${placa}","${estado}","${vehiculo}","${propietario}","${fecha}"\n`;
      });

      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `Historial_Alertas_AlertaVecinal_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('📥 Historial exportado como CSV.');
    });
  }

  // --- SERVICE WORKER REGISTRATION ---
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js')
        .then(reg => console.log('Service Worker registrado con éxito:', reg.scope))
        .catch(err => console.error('Error al registrar Service Worker:', err));
    });
  }

  // --- 🔒 ANTI-DEBUGGING & SECURITY HARDENING ---
  const securityBlockScreen = document.getElementById('securityBlockScreen');
  let securityBlockTriggered = false;

  function triggerSecurityBlock() {
    if (securityBlockTriggered) return;
    securityBlockTriggered = true;
    
    console.clear();
    console.error("🔒 BLOQUEO DE SEGURIDAD: Inspección de código / consola detectada.");

    // Destruir sesión y llaves simétricas
    localStorage.removeItem('user_session');
    sessionStorage.removeItem('session_crypto_key');
    sessionCryptoKey = null;

    // Desconectar WS
    if (ws) {
      try {
        ws.close();
      } catch (e) {}
    }

    // Limpiar intervalos
    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);
    if (fixedLensInterval) clearInterval(fixedLensInterval);
    stopAlarmSound();

    // Mostrar pantalla de bloqueo
    if (securityBlockScreen) {
      securityBlockScreen.style.display = 'flex';
    }
  }

  // 1. Detección por diferencia de tamaño de ventana (consola acoplada)
  function checkWindowDimensions() {
    const threshold = 160;
    const widthDiff = window.outerWidth - window.innerWidth;
    const heightDiff = window.outerHeight - window.innerHeight;
    
    if (widthDiff > threshold || heightDiff > threshold) {
      triggerSecurityBlock();
    }
  }

  // 2. Detección por tiempo de ejecución de la sentencia 'debugger'
  function checkDebuggerDelay() {
    const startTime = Date.now();
    debugger; // Se detendrá o demorará si la consola del programador está abierta
    const endTime = Date.now();
    
    if (endTime - startTime > 100) {
      triggerSecurityBlock();
    }
  }

  // Ejecutar los monitoreos periódicamente
  setInterval(() => {
    checkWindowDimensions();
    checkDebuggerDelay();
  }, 1000);

  // Escuchar redimensiones para detectar si abren la consola
  window.addEventListener('resize', checkWindowDimensions);
});
