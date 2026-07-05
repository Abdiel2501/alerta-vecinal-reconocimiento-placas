document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Navigation & Headers
  const tabButtons = document.querySelectorAll('.tab-btn');
  const views = document.querySelectorAll('.view-section');
  const demoBadge = document.getElementById('demoBadge');
  const wsStatusDot = document.getElementById('wsStatusDot');
  const wsStatusText = document.getElementById('wsStatusText');

  // DOM Elements - Monitor Section
  const videoCanvas = document.getElementById('videoCanvas');
  const ctx = videoCanvas.getContext('2d');
  const placeholder = document.getElementById('videoPlaceholder');
  const videoPlaceholderMsg = document.getElementById('videoPlaceholderMsg');
  const videoSpinner = document.getElementById('videoSpinner');
  const recIndicator = document.getElementById('recIndicator');
  const videoMetaBadge = document.getElementById('videoMetaBadge');
  const listCamerasBtn = document.getElementById('listCamerasBtn');
  const rtspUrlInput = document.getElementById('rtspUrl');
  const applyRtspBtn = document.getElementById('applyRtspBtn');
  const activeCameraInfo = document.getElementById('activeCameraInfo');

  // DOM Elements - History Section
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const historyTableBody = document.getElementById('historyTableBody');
  const mobileHistoryList = document.getElementById('mobileHistoryList');

  // DOM Elements - Settings Section
  const serverIpInput = document.getElementById('serverIp');
  const serverPortInput = document.getElementById('serverPort');
  const connectBtn = document.getElementById('connectBtn');
  const demoModeToggle = document.getElementById('demoModeToggle');
  const triggerDemoAlertBtn = document.getElementById('triggerDemoAlertBtn');

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
  let demoCanvasInterval = null;
  let demoAlertInterval = null;
  let demoPlateIndex = 0;
  let lastDemoAlertTime = 0;
  let lastDemoPlate = '';
  
  // Load settings and history from localStorage
  let history = JSON.parse(localStorage.getItem('alert_history') || '[]');
  serverIpInput.value = localStorage.getItem('server_ip') || '127.0.0.1';
  serverPortInput.value = localStorage.getItem('server_port') || '8765';
  
  // Register Service Worker using relative path
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js')
      .then(reg => console.log('Service Worker registrado:', reg.scope))
      .catch(err => console.error('Error registrando Service Worker:', err));
  }

  // --- VIEW NAVIGATION TABS ---
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      views.forEach(v => v.classList.remove('active'));

      btn.classList.add('active');
      const target = btn.getAttribute('data-target');
      document.getElementById(target).classList.add('active');
    });
  });

  // --- SPEECH SYNTHESIS (TTS) ---
  function speakAlert(plate) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // Parar cualquier audio anterior
      // Deletrear la placa para mejor pronunciación
      const spelledPlate = plate.split('').join(' ');
      const utterance = new SpeechSynthesisUtterance(`Alerta, placa ${spelledPlate} con reporte de robo detectada`);
      utterance.lang = 'es-ES';
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }
  }

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
    // Formatear la hora legible
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
    }
  }

  function mergeHistoryFromServer(serverAlerts) {
    if (!serverAlerts || !Array.isArray(serverAlerts)) return;
    
    serverAlerts.forEach(alert => {
      // Evitar duplicados por placa y fecha exacta
      const exists = history.some(h => h.placa === alert.placa && h.timestamp === alert.timestamp);
      if (!exists) {
        const dateObj = new Date(alert.timestamp || Date.now());
        const timeStr = dateObj.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + 
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

    // Ordenar de más reciente a más antiguo
    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    if (history.length > 100) {
      history = history.slice(0, 100);
    }

    saveHistory();
    renderHistory();
  }

  // --- CRITICAL ALERT MODAL ---
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
      window.speechSynthesis.cancel(); // Silenciar al confirmar
    }
  });

  // --- WEBSOCKET CONNECTION & MANAGEMENT ---
  function connectWebSocket() {
    if (demoMode) return;

    const ip = serverIpInput.value.trim() || '127.0.0.1';
    const port = serverPortInput.value.trim() || '8765';
    
    // Persistir IPs en localStorage
    localStorage.setItem('server_ip', ip);
    localStorage.setItem('server_port', port);

    const wsUrl = `ws://${ip}:${port}/ws`;

    if (ws) {
      ws.close();
    }

    wsStatusText.textContent = 'Conectando...';
    wsStatusDot.className = 'dot connecting';
    connectBtn.textContent = 'Conectando...';
    
    videoSpinner.style.display = 'inline-block';
    videoPlaceholderMsg.textContent = 'Conectando al servidor IA...';
    placeholder.style.display = 'flex';

    ws = new WebSocket(wsUrl);
    ws.binaryType = 'blob';

    ws.onopen = () => {
      console.log('WS Conectado');
      wsStatusText.textContent = 'Conectado';
      wsStatusDot.className = 'dot connected';
      connectBtn.textContent = 'Desconectar';
      connectBtn.className = 'btn btn-alert';
      placeholder.style.display = 'none';
      recIndicator.style.display = 'flex';
      
      // Solicitar el historial reciente al servidor al iniciar
      ws.send(JSON.stringify({ "cmd": "get_history", "limite_historial": 15 }));
    };

    ws.onmessage = async (event) => {
      // Mensajes de texto (JSON)
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
            videoMetaBadge.textContent = `FPS: ${data.fps || '0.0'} | Clientes: ${data.clients || '0'}`;
          } 
          else if (data.type === 'cameras') {
            populateCamerasModal(data.list);
          }
          else if (data.type === 'frame_meta') {
            // Recibe metadatos justo antes del frame binario
            videoMetaBadge.textContent = `FPS: ${data.fps || '0.0'} | Clientes: ${data.clients || '0'}`;
          }
        } catch (err) {
          console.error('Error parseando JSON de WebSocket:', err);
        }
      } 
      // Mensajes binarios (Blobs de imágenes de la cámara)
      else if (event.data instanceof Blob) {
        try {
          const imageBitmap = await createImageBitmap(event.data);
          
          // Redimensionar canvas si es necesario para calzar con la cámara
          if (videoCanvas.width !== imageBitmap.width || videoCanvas.height !== imageBitmap.height) {
            videoCanvas.width = imageBitmap.width;
            videoCanvas.height = imageBitmap.height;
          }
          
          ctx.drawImage(imageBitmap, 0, 0);
          placeholder.style.display = 'none';
        } catch (err) {
          console.error('Error dibujando frame binario:', err);
        }
      }
    };

    ws.onclose = () => {
      console.log('WS Cerrado');
      wsStatusText.textContent = 'Desconectado';
      wsStatusDot.className = 'dot';
      connectBtn.textContent = 'Conectar';
      connectBtn.className = 'btn';
      recIndicator.style.display = 'none';
      placeholder.style.display = 'flex';
      videoSpinner.style.display = 'none';
      videoPlaceholderMsg.textContent = 'Servidor desconectado.';
      
      // Auto-reconexión programada
      if (!userDisconnected) {
        scheduleReconnect();
      }
    };

    ws.onerror = (err) => {
      console.error('WS Error:', err);
      wsStatusText.textContent = 'Error';
      wsStatusDot.className = 'dot';
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

  // --- MANUAL RTSP CAMERA SWITCHING ---
  applyRtspBtn.addEventListener('click', () => {
    const url = rtspUrlInput.value.trim();
    if (!url) return;
    
    if (demoMode) {
      activeCameraInfo.value = `[DEMO] ${url}`;
      return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        "cmd": "change_camera_url",
        "url": url
      }));
      console.log('Enviando comando para cambiar cámara URL:', url);
    } else {
      alert('Debes estar conectado al servidor para cambiar la cámara.');
    }
  });

  // --- SYSTEM CAMERAS SCAN & SELECT ---
  listCamerasBtn.addEventListener('click', () => {
    if (demoMode) {
      populateCamerasModal(['📹 Cámara Integrada (Simulada)', 'Cámara USB Externa (Simulada)']);
      return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ "cmd": "list_cameras" }));
      console.log('Solicitando listado de cámaras...');
    } else {
      alert('Debes estar conectado al servidor para escanear cámaras.');
    }
  });

  function populateCamerasModal(camerasList) {
    cameraListContainer.innerHTML = '';
    
    if (!camerasList || camerasList.length === 0) {
      cameraListContainer.innerHTML = `<p style="color:var(--text-secondary); text-align:center;">No se detectaron cámaras en el sistema.</p>`;
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
            console.log(`Cambiando a cámara USB índice ${index}: ${cam}`);
          }
          cameraSelectModal.classList.remove('active');
        });
        cameraListContainer.appendChild(btn);
      });
    }

    cameraSelectModal.classList.add('active');
  }

  closeCameraModalBtn.addEventListener('click', () => {
    cameraSelectModal.classList.remove('active');
  });

  // --- DEMO MODE MODULE ---
  function startDemoMode() {
    demoMode = true;
    demoBadge.style.display = 'inline-block';
    triggerDemoAlertBtn.style.display = 'inline-block';
    
    // UI Status
    wsStatusText.textContent = 'Conectado (Demo)';
    wsStatusDot.className = 'dot connected';
    placeholder.style.display = 'none';
    recIndicator.style.display = 'flex';
    
    if (ws) {
      ws.close();
    }
    
    // Cargar historial demo si está vacío
    if (history.length === 0) {
      preloadDemoHistory();
    }

    // Iniciar Canvas animado de Radar
    startDemoCanvasAnimation();

    // Iniciar Generador Automático de Alertas Demo cada 15 segundos
    startDemoAlertGenerator();
  }

  function stopDemoMode() {
    demoMode = false;
    demoBadge.style.display = 'none';
    triggerDemoAlertBtn.style.display = 'none';

    // UI Status
    wsStatusText.textContent = 'Desconectado';
    wsStatusDot.className = 'dot';
    recIndicator.style.display = 'none';
    placeholder.style.display = 'flex';

    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    if (demoAlertInterval) clearInterval(demoAlertInterval);

    // Reconectar WebSocket real
    userDisconnected = false;
    connectWebSocket();
  }

  function startDemoCanvasAnimation() {
    if (demoCanvasInterval) clearInterval(demoCanvasInterval);
    
    let angle = 0;
    videoCanvas.width = 640;
    videoCanvas.height = 360;

    demoCanvasInterval = setInterval(() => {
      ctx.fillStyle = '#0E121A'; // Fondo oscuro
      ctx.fillRect(0, 0, videoCanvas.width, videoCanvas.height);

      // Dibujar cuadrícula de fondo
      ctx.strokeStyle = 'rgba(0, 194, 209, 0.1)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = 0; x < videoCanvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, videoCanvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < videoCanvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(videoCanvas.width, y);
        ctx.stroke();
      }

      // Dibujar línea de barrido de radar
      ctx.strokeStyle = 'rgba(0, 194, 209, 0.4)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      let scanX = (angle % videoCanvas.width);
      ctx.moveTo(scanX, 0);
      ctx.lineTo(scanX, videoCanvas.height);
      ctx.stroke();

      // Relleno degradado que sigue el escaneo
      let gradient = ctx.createLinearGradient(scanX - 120, 0, scanX, 0);
      gradient.addColorStop(0, 'rgba(0, 194, 209, 0)');
      gradient.addColorStop(1, 'rgba(0, 194, 209, 0.15)');
      ctx.fillStyle = gradient;
      ctx.fillRect(scanX - 120, 0, 120, videoCanvas.height);

      // Dibujar cajas simuladas de detección
      ctx.strokeStyle = 'var(--primary-color)';
      ctx.lineWidth = 2;
      ctx.strokeRect(150, 100, 120, 80);
      ctx.fillStyle = 'var(--primary-color)';
      ctx.font = '12px Outfit';
      ctx.fillText('Vehículo [ID: 42] 94%', 150, 92);

      // Si hay alerta crítica demo activa (menos de 5 segundos)
      if (Date.now() - lastDemoAlertTime < 5000) {
        ctx.strokeStyle = 'var(--alert-color)';
        ctx.lineWidth = 3;
        ctx.strokeRect(340, 140, 160, 90);
        ctx.fillStyle = 'var(--alert-color)';
        ctx.font = '700 13px Outfit';
        ctx.fillText('⚠️ PLACA REPORTADA: ' + lastDemoPlate, 340, 130);
      }

      // Texto de Metadatos
      ctx.fillStyle = '#F8F9FA';
      ctx.font = '600 13px Outfit';
      ctx.fillText('MONITOR ACTIVADO - SIMULACIÓN DE CÁMARA', 20, 30);
      
      angle += 5;
    }, 1000 / 30); // 30 FPS
  }

  function startDemoAlertGenerator() {
    if (demoAlertInterval) clearInterval(demoAlertInterval);

    demoAlertInterval = setInterval(() => {
      triggerDemoAlert();
    }, 15000);
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
  // Switch toggle event
  demoModeToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
      startDemoMode();
    } else {
      stopDemoMode();
    }
  });

  triggerDemoAlertBtn.addEventListener('click', triggerDemoAlert);

  // Clear local logs
  clearHistoryBtn.addEventListener('click', () => {
    if (confirm('¿Seguro que deseas vaciar el historial local?')) {
      history = [];
      saveHistory();
      renderHistory();
    }
  });

  // Check URL query parameters to boot in Demo Mode
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('demo') === 'true') {
    demoModeToggle.checked = true;
    startDemoMode();
  } else {
    // Initial standard loading
    renderHistory();
    setTimeout(connectWebSocket, 500);
  }
});
