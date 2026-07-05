document.addEventListener('DOMContentLoaded', () => {
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
  let history = JSON.parse(localStorage.getItem('alert_history') || '[]');
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
  // Lanzamiento de la pantalla de carga (Splash Screen) por 2 segundos
  setTimeout(() => {
    splashScreen.classList.add('fade-out');
    
    // Validar si hay sesión guardada
    const savedSession = JSON.parse(localStorage.getItem('user_session'));
    if (savedSession) {
      logInSuccess(savedSession);
    } else {
      loginScreen.style.display = 'flex';
      appLayout.style.display = 'none';
    }
  }, 2000);

  function logInSuccess(session) {
    localStorage.setItem('user_session', JSON.stringify(session));
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
    const email = loginEmail.value.trim();
    const password = loginPassword.value.trim();

    if (email === 'admin@alertavecinal.com' && password === 'admin123') {
      logInSuccess({
        name: 'Administrador',
        email: email,
        provider: 'credentials'
      });
    } else {
      alert('Credenciales incorrectas. Prueba con admin@alertavecinal.com / admin123');
    }
  });

  googleLoginBtn.addEventListener('click', () => {
    googleLoginBtn.textContent = 'Autenticando con Google...';
    googleLoginBtn.disabled = true;

    // Simular el Login con Google
    setTimeout(() => {
      googleLoginBtn.textContent = 'Iniciar Sesión con Google';
      googleLoginBtn.disabled = false;
      logInSuccess({
        name: 'Jorge G. Lara',
        email: 'jorgegalara13@gmail.com',
        provider: 'google'
      });
    }, 1000);
  });

  logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('user_session');
    
    if (ws) ws.close();
    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);
    if (fixedLensInterval) clearInterval(fixedLensInterval);
    
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
  function saveHistory() {
    localStorage.setItem('alert_history', JSON.stringify(history));
  }

  function renderHistory() {
    historyTableBody.innerHTML = '';
    mobileHistoryList.innerHTML = '';

    if (history.length === 0) {
      const emptyRow = `<tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">No hay detecciones registradas</td></tr>`;
      historyTableBody.innerHTML = emptyRow;
      mobileHistoryList.innerHTML = `<div style="text-align:center; color: var(--text-secondary); padding: 20px;">No hay detecciones registradas</div>`;
      return;
    }

    history.forEach(item => {
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

  // --- CRITICAL MODAL SCREEN ---
  function showCriticalModal(alertData) {
    criticalPlate.textContent = alertData.placa;
    criticalModel.textContent = alertData.modelo || '?';
    criticalColor.textContent = alertData.color || '?';
    criticalOwner.textContent = alertData.propietario || '?';
    criticalTime.textContent = alertData.timeStr || new Date().toLocaleTimeString();
    
    criticalAlertModal.classList.add('active');
    speakAlert(alertData.placa);
  }

  dismissAlertBtn.addEventListener('click', () => {
    criticalAlertModal.classList.remove('active');
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
    
    // Si la IP/Dirección ya contiene un esquema de websocket
    if (ip.startsWith('ws://') || ip.startsWith('wss://')) {
      wsUrl = ip;
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else if (ip.startsWith('http://') || ip.startsWith('https://')) {
      wsUrl = ip.replace(/^http/, 'ws');
      if (!wsUrl.endsWith('/ws')) {
        wsUrl = wsUrl.replace(/\/?$/, '/ws');
      }
    } else {
      // Es una IP o un dominio sin protocolo
      const protocol = (window.location.protocol === 'https:') ? 'wss' : 'ws';
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
});
