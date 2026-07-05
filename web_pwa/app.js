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
  const loginEmail = document.getElementById('loginEmail');
  const loginPassword = document.getElementById('loginPassword');
  const normalLoginBtn = document.getElementById('normalLoginBtn');
  const googleLoginBtn = document.getElementById('googleLoginBtn');
  const googleBtnContainer = document.getElementById('googleBtnContainer');
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
  const applyRtspBtn = document.getElementById('applyRtspBtn');
  const activeCameraInfo = document.getElementById('activeCameraInfo');
  
  const serverIpInput = document.getElementById('serverIp');
  const serverPortInput = document.getElementById('serverPort');
  const connectBtn = document.getElementById('connectBtn');
  
  const telegramTokenInput = document.getElementById('telegramToken');
  const telegramChatIdInput = document.getElementById('telegramChatId');
  const saveTelegramBtn = document.getElementById('saveTelegramBtn');
  
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

  // App State Variables
  let ws = null;
  let reconnectTimeout = null;
  let userDisconnected = false;
  let demoMode = false;
  let isAiActive = true;
  
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
  serverIpInput.value = localStorage.getItem('server_ip') || '127.0.0.1';
  serverPortInput.value = localStorage.getItem('server_port') || '8765';
  telegramTokenInput.value = localStorage.getItem('telegram_token') || '';
  telegramChatIdInput.value = localStorage.getItem('telegram_chat_id') || '';

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

      try {
        google.accounts.id.initialize({
          client_id: CONFIG.GOOGLE_CLIENT_ID,
          callback: handleGoogleCredentialResponse
        });

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
      } catch (err) {
        console.error("Error inicializando Google Sign-In real:", err);
        if (googleLoginBtn) googleLoginBtn.style.display = 'flex';
        if (googleBtnContainer) googleBtnContainer.style.display = 'none';
      }
    } else {
      if (googleLoginBtn) googleLoginBtn.style.display = 'flex';
      if (googleBtnContainer) googleBtnContainer.style.display = 'none';
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

  acceptConsentBtn.addEventListener('click', () => {
    localStorage.setItem('privacy_accepted', 'true');
    privacyConsentModal.classList.remove('active');
    checkSessionAndStart();
  });

  declineConsentBtn.addEventListener('click', () => {
    alert('Debe aceptar el Aviso de Privacidad y Consentimiento para ingresar y utilizar la plataforma AlertaVecinal.');
  });

  function logInSuccess(session) {
    localStorage.setItem('user_session', JSON.stringify(session));
    
    // Cargar historial cifrado localmente
    history = loadHistoryEncrypted();

    loginScreen.style.display = 'none';
    appLayout.style.display = 'flex';

    if (session.provider === 'google') {
      googleProfileCard.style.display = 'block';
      profileName.textContent = session.name;
      profileEmail.textContent = session.email;
      userInitial.textContent = session.name.charAt(0);
    } else {
      googleProfileCard.style.display = 'none';
    }

    showToast(`👋 ¡Bienvenido de nuevo, ${session.name}!`);
    
    // Iniciar renderizado estático del lente fijo
    startFixedLensRender();

    // Iniciar conexión automática
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('demo') === 'true' || demoModeToggle.checked) {
      demoModeToggle.checked = true;
      startDemoMode();
    } else {
      renderHistory();
      setTimeout(connectWebSocket, 500);
    }
  }

  normalLoginBtn.addEventListener('click', () => {
    if (checkLockout()) return;

    const email = loginEmail.value.trim();
    const password = loginPassword.value.trim();

    if (email === 'admin@alertavecinal.com' && password === 'admin123') {
      authFailures = 0;
      localStorage.removeItem('auth_failures');
      localStorage.removeItem('lockout_timestamp');
      
      deriveSessionKey(password);

      logInSuccess({
        name: 'Administrador',
        email: email,
        provider: 'credentials'
      });
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

  // --- ⤢ DUAL-LENS COLLAPSE & EXPAND LOGIC ---
  toggleFixedBtn.addEventListener('click', () => {
    const isExpanded = lensPtzContainer.classList.contains('collapsed');
    
    if (isExpanded) {
      // Contraer
      lensPtzContainer.classList.remove('collapsed');
      toggleFixedBtn.textContent = '⤢';
      ptzOverlay.style.display = 'flex';
      zoomOverlay.style.display = 'flex';
    } else {
      // Expandir
      lensPtzContainer.classList.add('collapsed');
      toggleFixedBtn.textContent = '⤡';
    }
  });

  togglePtzBtn.addEventListener('click', () => {
    const isExpanded = lensFixedContainer.classList.contains('collapsed');
    
    if (isExpanded) {
      // Contraer
      lensFixedContainer.classList.remove('collapsed');
      togglePtzBtn.textContent = '⤢';
    } else {
      // Expandir
      lensFixedContainer.classList.add('collapsed');
      togglePtzBtn.textContent = '⤡';
    }
  });

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

  ptzCenterBtn.addEventListener('click', () => {
    showToast('🕹️ Cámara centrada.');
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        "cmd": "ptz",
        "action": "center"
      }));
    }

    if (demoMode) {
      ptzOffsetX = 0;
      ptzOffsetY = 0;
      demoZoomScale = 1.0;
    }
  });

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
  saveTelegramBtn.addEventListener('click', () => {
    const token = telegramTokenInput.value.trim();
    const chatId = telegramChatIdInput.value.trim();

    localStorage.setItem('telegram_token', token);
    localStorage.setItem('telegram_chat_id', chatId);

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

  // --- HISTORY MANAGEMENT ---
  function loadHistoryEncrypted() {
    try {
      const encryptedData = localStorage.getItem('alert_history');
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
      localStorage.setItem('alert_history', encryptedData);
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

    const filtered = history.filter(item => {
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

    // Agregar al historial local
    history.unshift(formattedAlert);
    if (history.length > 100) {
      history.pop();
    }

    saveHistory();
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
    playAlarmSound();
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
    
    localStorage.setItem('server_ip', ip);
    localStorage.setItem('server_port', port);

    let wsUrl = '';
    
    // Enforce WSS (WebSocket Secure) for protection against sniffing
    if (ip.startsWith('ws://') || ip.startsWith('wss://')) {
      wsUrl = ip.replace(/^ws:\/\//, 'wss://');
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else if (ip.startsWith('http://') || ip.startsWith('https://')) {
      wsUrl = ip.replace(/^http/, 'wss');
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else {
      const protocol = 'wss';
      const isDomain = ip.includes('.') && !/^[0-9.]+$/.test(ip) && ip !== 'localhost';
      
      if (isDomain && (port === '80' || port === '443' || port === '')) {
        wsUrl = `${protocol}://${ip}/ws`;
      } else {
        wsUrl = `${protocol}://${ip}:${port}/ws`;
      }
    }

    if (ws) ws.close();

    wsStatusText.textContent = 'Conectando...';
    wsStatusDot.className = 'dot connecting';
    connectBtn.textContent = 'Conectando...';
    
    videoSpinner.style.display = 'inline-block';
    ptzMsg.textContent = 'Conectando al servidor IA...';
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
      
      const token = telegramTokenInput.value.trim();
      const chatId = telegramChatIdInput.value.trim();
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
            videoMetaText.textContent = `FPS de Servidor: ${data.fps || '0.0'} | Clientes: ${data.clients || '0'}`;
          } 
          else if (data.type === 'cameras') {
            populateCamerasModal(data.list);
          }
          else if (data.type === 'frame_meta') {
            videoMetaText.textContent = `FPS de Servidor: ${data.fps || '0.0'} | Clientes: ${data.clients || '0'}`;
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
      wsStatusText.textContent = 'Desconectado';
      wsStatusDot.className = 'dot';
      connectBtn.textContent = 'Conectar';
      connectBtn.className = 'btn';
      recIndicator.style.display = 'none';
      placeholderPtz.style.display = 'flex';
      videoSpinner.style.display = 'none';
      ptzMsg.textContent = 'Servidor desconectado.';
      
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
    
    wsStatusText.textContent = 'Reconectando...';
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
      alert('Conéctate al servidor para cambiar la cámara.');
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
      alert('Conéctate al servidor para escanear cámaras.');
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
    
    wsStatusText.textContent = 'Conectado (Demo)';
    wsStatusDot.className = 'dot connected';
    placeholderPtz.style.display = 'none';
    recIndicator.style.display = 'flex';
    
    if (ws) ws.close();
    
    if (history.length === 0) {
      preloadDemoHistory();
    }

    startDemoCanvasAnimation();
    startDemoAlertGenerator();
    showToast('🚀 Modo Demo iniciado. Puedes usar los joysticks e interruptores.');
  }

  function stopDemoMode() {
    demoMode = false;
    demoBadge.style.display = 'none';
    triggerDemoAlertBtn.style.display = 'none';

    wsStatusText.textContent = 'Desconectado';
    wsStatusDot.className = 'dot';
    recIndicator.style.display = 'none';
    placeholderPtz.style.display = 'flex';

    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);

    userDisconnected = false;
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
      const exists = history.some(h => h.placa === alert.placa);
      if (!exists) {
        const dateObj = new Date(alert.timestamp);
        const timeStr = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) + ' ' + 
                        dateObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        
        history.push({
          ...alert,
          timeStr: timeStr
        });
      }
    });

    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    saveHistory();
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
      history = [];
      saveHistory();
      renderHistory();
      showToast('🗑️ Historial vaciado.');
    }
  });

  // --- MANUAL THEME SELECTION LOGIC ---
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  let currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
  
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon(currentTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      localStorage.setItem('theme', currentTheme);
      updateThemeIcon(currentTheme);
      showToast(`🌓 Modo ${currentTheme === 'dark' ? 'oscuro' : 'claro'} activado`);
    });
  }

  function updateThemeIcon(theme) {
    if (!themeToggleBtn) return;
    themeToggleBtn.textContent = (theme === 'dark') ? '☀️' : '🌙';
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
      if (history.length === 0) {
        alert('No hay registros en el historial para exportar.');
        return;
      }

      let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // UTF-8 BOM for Excel
      csvContent += "Placa,Estado,Modelo y Color,Propietario,Fecha y Hora\n";

      history.forEach(item => {
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
