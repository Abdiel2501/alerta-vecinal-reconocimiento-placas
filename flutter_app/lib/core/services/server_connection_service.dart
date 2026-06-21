import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

// ─── Modelos de datos del servidor ───────────────────────────────────────────

/// Estado de la conexión WebSocket con el servidor IA
enum ServerConnectionState {
  disconnected,
  discovering, // Buscando el servidor en la red local con mDNS
  connecting,
  connected,
  error,
}

/// Alerta recibida desde el servidor IA en tiempo real
class ServerAlert {
  final String placa;
  final String placaBd;
  final double similitud;
  final String modelo;
  final String color;
  final String propietario;
  final bool esRobado;
  final int trackId;
  final DateTime timestamp;
  final String? fotoVehiculoPath;
  final String? fotoPlacaPath;

  ServerAlert({
    required this.placa,
    required this.placaBd,
    required this.similitud,
    required this.modelo,
    required this.color,
    required this.propietario,
    required this.esRobado,
    required this.trackId,
    required this.timestamp,
    this.fotoVehiculoPath,
    this.fotoPlacaPath,
  });

  factory ServerAlert.fromJson(Map<String, dynamic> j) => ServerAlert(
        placa: j['placa'] as String? ?? '',
        placaBd: j['placa_bd'] as String? ?? j['placa'] as String? ?? '',
        similitud: (j['similitud'] as num?)?.toDouble() ?? 100.0,
        modelo: j['modelo'] as String? ?? '?',
        color: j['color'] as String? ?? '?',
        propietario: j['propietario'] as String? ?? '?',
        esRobado: j['es_robado'] as bool? ?? true,
        trackId: j['track_id'] as int? ?? 0,
        timestamp: j['timestamp'] != null
            ? DateTime.tryParse(j['timestamp'] as String) ?? DateTime.now()
            : DateTime.now(),
        fotoVehiculoPath: j['foto_vehiculo'] as String?,
        fotoPlacaPath: j['foto_placa'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'placa': placa,
        'placa_bd': placaBd,
        'similitud': similitud,
        'modelo': modelo,
        'color': color,
        'propietario': propietario,
        'es_robado': esRobado,
        'track_id': trackId,
        'timestamp': timestamp.toIso8601String(),
        'foto_vehiculo': fotoVehiculoPath,
        'foto_placa': fotoPlacaPath,
      };
}

// ─── Servicio principal ───────────────────────────────────────────────────────

/// Servicio que gestiona la conexión WebSocket entre Flutter y el Servidor IA.
///
/// Comportamiento de arranque:
///  1. Lanza servidor_ia.py en segundo plano si no está corriendo.
///  2. Espera hasta 60 segundos a que /health responda (Python tarda en cargar YOLO).
///  3. Conecta por WebSocket y mantiene la conexión con reconexión automática.
class ServerConnectionService extends ChangeNotifier {
  // ── Estado ─────────────────────────────────────────────────────────────────
  ServerConnectionState _state = ServerConnectionState.disconnected;
  String _serverIp = 'localhost';
  int _serverPort = 8765;
  String _errorMessage = '';
  double _fps = 0.0;
  int _clientsCount = 0;
  String _currentCamera = '';
  List<Map<String, dynamic>> _availableCameras = [];
  List<ServerAlert> _alerts = [];
  Uint8List? _latestFrame;

  // ── Internos ───────────────────────────────────────────────────────────────
  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  Timer? _discoveryTimer;
  bool _userRequestedDisconnect = false;
  bool _isDisposed = false;
  Process? _backendProcess;
  int _reconnectAttempts = 0;
  bool _backendStarted = false;

  static const String _prefIpKey = 'server_ip';
  static const String _prefPortKey = 'server_port';

  // ── Getters ────────────────────────────────────────────────────────────────
  ServerConnectionState get state => _state;
  String get serverIp => _serverIp;
  int get serverPort => _serverPort;
  String get serverAddress => '$_serverIp:$_serverPort';
  String get errorMessage => _errorMessage;
  double get fps => _fps;
  int get clientsCount => _clientsCount;
  String get currentCamera => _currentCamera;
  List<Map<String, dynamic>> get availableCameras =>
      List.unmodifiable(_availableCameras);
  List<ServerAlert> get alerts => List.unmodifiable(_alerts);
  Uint8List? get latestFrame => _latestFrame;
  bool get isConnected => _state == ServerConnectionState.connected;

  // ─── Inicialización ────────────────────────────────────────────────────────

  Future<void> initialize() async {
    if (_isDisposed) return;

    final prefs = await SharedPreferences.getInstance();
    _serverIp = prefs.getString(_prefIpKey) ?? 'localhost';
    _serverPort = prefs.getInt(_prefPortKey) ?? 8765;

    // Limpiar puertos dinámicos/corruptos guardados por versiones anteriores
    if (_serverPort > 50000 || _serverPort < 1024) {
      _serverPort = 8765;
      await prefs.setInt(_prefPortKey, 8765);
    }

    // Normalizar IPs locales
    if (_serverIp == '127.0.0.1') _serverIp = 'localhost';

    // Arrancar el backend y esperar a que esté listo antes de conectar
    if (_serverIp == 'localhost') {
      await _ensureBackendRunning();
    } else {
      // Servidor remoto: conectar directamente
      _reconnectAttempts = 0;
      _doConnect();
    }
  }

  // ─── Gestión del proceso del servidor IA ──────────────────────────────────

  /// Verifica si el servidor ya está activo, si no lo lanza y espera a que esté listo.
  Future<void> _ensureBackendRunning() async {
    if (_isDisposed) return;

    // Si ya responde, conectar directamente
    if (await _healthCheck()) {
      debugPrint('[ServerConn] Servidor ya activo — conectando...');
      _reconnectAttempts = 0;
      _doConnect();
      return;
    }

    // Lanzar el proceso si aún no lo hemos hecho
    if (!_backendStarted) {
      await _launchBackend();
    }

    // Esperar a que el servidor esté listo (hasta 90 segundos para cargar YOLO + GPU)
    debugPrint('[ServerConn] Esperando a que el servidor de IA arranque...');
    _setState(ServerConnectionState.connecting);
    _errorMessage = 'Iniciando servidor de IA...';
    if (!_isDisposed) notifyListeners();

    bool ready = false;
    for (int i = 0; i < 90; i++) {
      if (_isDisposed) return;
      await Future.delayed(const Duration(seconds: 1));
      if (await _healthCheck()) {
        ready = true;
        break;
      }
      // Actualizar mensaje para que el usuario vea progreso
      if (i % 5 == 4) {
        debugPrint('[ServerConn] Cargando IA... ${i + 1}s');
      }
    }

    if (!_isDisposed) {
      if (ready) {
        debugPrint('[ServerConn] ✅ Servidor listo — conectando WebSocket');
        _reconnectAttempts = 0;
        _doConnect();
      } else {
        _setState(ServerConnectionState.error);
        _errorMessage =
            'El servidor de IA tardó demasiado en iniciar.\nVerifica que Python y los modelos estén instalados correctamente.';
        notifyListeners();
      }
    }
  }

  /// Hace una petición HTTP al endpoint /health. Devuelve true si responde 200.
  Future<bool> _healthCheck() async {
    try {
      final client = HttpClient()
        ..connectionTimeout = const Duration(milliseconds: 500);
      final uri = Uri.parse('http://$_serverIp:$_serverPort/health');
      final req = await client.getUrl(uri).timeout(const Duration(milliseconds: 600));
      final res = await req.close().timeout(const Duration(milliseconds: 600));
      await res.drain<void>();
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Lanza el proceso Python del servidor IA en segundo plano.
  Future<void> _launchBackend() async {
    if (!Platform.isWindows && !Platform.isLinux && !Platform.isMacOS) return;
    _backendStarted = true;

    try {
      // Buscar servidor_ia.py subiendo hasta 5 niveles desde el directorio actual
      Directory dir = Directory.current;
      File? script;
      String? workingDir;

      for (int i = 0; i < 5; i++) {
        final p1 = '${dir.path}/servidor_ia.py';
        final p2 = '${dir.path}/../servidor_ia.py';
        if (File(p1).existsSync()) {
          script = File(p1);
          workingDir = dir.path;
          break;
        } else if (File(p2).existsSync()) {
          script = File(p2);
          workingDir = dir.parent.path;
          break;
        }
        dir = dir.parent;
      }

      if (script == null) {
        debugPrint('[ServerConn] ⚠️ No se encontró servidor_ia.py');
        return;
      }

      debugPrint('[ServerConn] Lanzando servidor IA: ${script.path}');
      _backendProcess = await Process.start(
        'python',
        [script.path],
        workingDirectory: workingDir,
        // Forzar UTF-8 en la salida de Python para evitar errores de codificación
        environment: {
          ...Platform.environment,
          'PYTHONIOENCODING': 'utf-8',
          'PYTHONLEGACYWINDOWSSTDIO': '0',
        },
        runInShell: false,
      );

      // Capturar logs — allowMalformed=true evita crashes por emojis en Windows ANSI
      _backendProcess!.stdout
          .transform(Utf8Decoder(allowMalformed: true))
          .transform(const LineSplitter())
          .listen((line) => debugPrint('[IA] $line'));
      _backendProcess!.stderr
          .transform(Utf8Decoder(allowMalformed: true))
          .transform(const LineSplitter())
          .listen((line) => debugPrint('[IA ERR] $line'));

      debugPrint('[ServerConn] Proceso IA lanzado (PID: ${_backendProcess!.pid})');
    } catch (e) {
      debugPrint('[ServerConn] Error lanzando servidor IA: $e');
      _backendStarted = false;
    }
  }

  /// Detiene de manera segura el proceso de fondo del Servidor IA
  void _killBackend() {
    if (_backendProcess != null) {
      try {
        _backendProcess!.kill();
      } catch (_) {}
      _backendProcess = null;
      _backendStarted = false;
    }
  }

  // ─── Auto-descubrimiento en LAN ───────────────────────────────────────────

  /// Escanea la red local buscando el servidor IA por el endpoint /health.
  Future<void> discoverServer() async {
    _setState(ServerConnectionState.discovering);
    _errorMessage = 'Buscando servidor en la red local...';
    notifyListeners();

    // Primero intentar localhost
    if (await _healthCheck()) {
      await connect('localhost', port: _serverPort, saveIp: true);
      return;
    }

    // Obtener la subnet local
    String subnet = '192.168.1';
    try {
      final interfaces = await NetworkInterface.list();
      for (final iface in interfaces) {
        for (final addr in iface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            final parts = addr.address.split('.');
            if (parts.length == 4) {
              subnet = '${parts[0]}.${parts[1]}.${parts[2]}';
              break;
            }
          }
        }
      }
    } catch (_) {}

    debugPrint('[ServerConn] Escaneando $subnet.0/24 en puerto $_serverPort');

    final futures = <Future>[];
    for (int i = 1; i <= 254; i++) {
      futures.add(_checkHost('$subnet.$i'));
    }
    futures.add(_checkHost('127.0.0.1'));

    for (int i = 0; i < futures.length; i += 30) {
      final batch = futures.sublist(i, (i + 30).clamp(0, futures.length));
      await Future.wait(batch);
      if (_state == ServerConnectionState.connected) return;
    }

    if (_state != ServerConnectionState.connected) {
      _setState(ServerConnectionState.error);
      _errorMessage =
          'No se encontró el Servidor IA en la red local.\nVerifica que el servidor esté encendido.';
      notifyListeners();
    }
  }

  Future<void> _checkHost(String host) async {
    if (_state == ServerConnectionState.connected) return;
    try {
      final client = HttpClient()
        ..connectionTimeout = const Duration(milliseconds: 400);
      final req = await client
          .getUrl(Uri.parse('http://$host:$_serverPort/health'))
          .timeout(const Duration(milliseconds: 500));
      final res = await req.close().timeout(const Duration(milliseconds: 500));
      await res.drain<void>();
      if (res.statusCode == 200) {
        debugPrint('[ServerConn] ✅ Servidor en $host');
        await connect(host, port: _serverPort, saveIp: true);
      }
    } catch (_) {}
  }

  // ─── Conexión WebSocket ────────────────────────────────────────────────────

  Future<void> connect(String ip,
      {int? port, bool saveIp = true}) async {
    if (_isDisposed) return;
    if (_state == ServerConnectionState.connected && _serverIp == ip) return;

    _userRequestedDisconnect = false;
    _serverIp = ip;
    if (port != null) _serverPort = port;

    if (saveIp) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefIpKey, ip);
      await prefs.setInt(_prefPortKey, _serverPort);
    }

    _setState(ServerConnectionState.connecting);
    notifyListeners();
    _reconnectAttempts = 0;
    _doConnect();
  }

  void _doConnect() {
    if (_isDisposed || _userRequestedDisconnect) return;
    _cleanup(cancelReconnect: false);

    final uri = Uri.parse('ws://$_serverIp:$_serverPort/ws');
    debugPrint('[ServerConn] Conectando a $uri (intento ${_reconnectAttempts + 1})');

    try {
      _channel = WebSocketChannel.connect(uri);

      // Esperar handshake con timeout
      _channel!.ready.timeout(const Duration(seconds: 8)).then((_) {
        if (_isDisposed || _userRequestedDisconnect) return;
        _reconnectAttempts = 0;
        _setState(ServerConnectionState.connected);
        _errorMessage = '';
        notifyListeners();
        debugPrint('[ServerConn] ✅ Conectado al servidor IA');

        // Ping cada 20s para mantener la conexión viva (el servidor cierra a los 30s sin actividad)
        _discoveryTimer?.cancel();
        _discoveryTimer = Timer.periodic(const Duration(seconds: 20), (_) {
          if (isConnected && _channel != null) {
            try {
              _channel!.sink.add(json.encode({'cmd': 'ping'}));
            } catch (_) {}
          }
        });

        _sub = _channel!.stream.listen(
          _onMessage,
          onError: _onError,
          onDone: _onDone,
          cancelOnError: false,
        );
      }).catchError((e) {
        debugPrint('[ServerConn] Handshake fallido: $e');
        _onError(e);
      });
    } catch (e) {
      debugPrint('[ServerConn] Error al conectar: $e');
      _onError(e);
    }
  }

  // ─── Decodificación eficiente de frames ───────────────────────────────────

  /// Decodifica Base64 de forma eficiente sin copias innecesarias.
  Uint8List? _safeDecodeBase64(String raw) {
    try {
      // El servidor envía Base64 limpio sin saltos de línea — solo arreglamos el padding
      final rem = raw.length % 4;
      if (rem > 0) raw = raw.padRight(raw.length + (4 - rem), '=');
      return base64Decode(raw);
    } catch (e) {
      debugPrint('[ServerConn] Frame Base64 inválido descartado: $e');
      return null;
    }
  }

  // ─── Procesamiento de mensajes ────────────────────────────────────────────

  /// Metadata del último frame_meta recibido (fps, clients)
  double _pendingFps = 0.0;
  int _pendingClients = 0;

  void _onMessage(dynamic raw) {
    if (_isDisposed) return;
    try {
      // Mensajes binarios = JPEG crudo del frame
      if (raw is Uint8List) {
        _latestFrame = raw;
        _fps = _pendingFps > 0 ? _pendingFps : _fps;
        _clientsCount = _pendingClients > 0 ? _pendingClients : _clientsCount;
        notifyListeners();
        return;
      }

      // Mensajes de texto = JSON de control/metadatos
      // Decodificamos con allowMalformed para no crashear si Python envía
      // caracteres especiales (emojis) con codificación incorrecta en Windows.
      String rawStr;
      if (raw is List<int>) {
        rawStr = const Utf8Decoder(allowMalformed: true).convert(raw);
      } else {
        rawStr = raw as String;
      }
      final Map<String, dynamic> msg = json.decode(rawStr);
      final type = msg['type'] as String?;

      switch (type) {
        case 'frame_meta':
          // Metadatos del frame binario que viene justo después
          _pendingFps = (msg['fps'] as num?)?.toDouble() ?? _fps;
          _pendingClients = msg['clients'] as int? ?? _clientsCount;
          break;

        case 'frame':
        case 'fotograma':
          // Compatibilidad con protocolo base64 antiguo
          final b64 = msg['data'] as String?;
          if (b64 != null && b64.isNotEmpty) {
            final decoded = _safeDecodeBase64(b64);
            if (decoded != null) _latestFrame = decoded;
          }
          _fps = (msg['fps'] as num?)?.toDouble() ?? _fps;
          _clientsCount = msg['clients'] as int? ?? _clientsCount;
          notifyListeners();

        case 'alert':
          final alert = ServerAlert.fromJson(msg);
          _alerts.insert(0, alert);
          if (_alerts.length > 100) _alerts.removeLast();
          notifyListeners();

        case 'cameras':
          final list = msg['list'] as List<dynamic>?;
          if (list != null) {
            _availableCameras = list.cast<Map<String, dynamic>>();
            notifyListeners();
          }

        case 'history':
          final list = msg['alerts'] as List<dynamic>?;
          if (list != null) {
            _alerts = list
                .cast<Map<String, dynamic>>()
                .map((j) => ServerAlert.fromJson(j))
                .toList();
            notifyListeners();
          }

        case 'status':
          _fps = (msg['fps'] as num?)?.toDouble() ?? _fps;
          _currentCamera = msg['camera'] as String? ?? _currentCamera;
          final cams = msg['cameras'] as List<dynamic>?;
          if (cams != null) {
            _availableCameras = cams.cast<Map<String, dynamic>>();
          }
          notifyListeners();

        case 'ping':
          break;

        default:
          break;
      }
    } catch (e) {
      debugPrint('[ServerConn] Error parseando mensaje: $e');
    }
  }

  void _onError(dynamic error) {
    if (_isDisposed) return;
    debugPrint('[ServerConn] Error WebSocket: $error');
    _setState(ServerConnectionState.error);
    _latestFrame = null;
    notifyListeners();
    _scheduleReconnect();
  }

  void _onDone() {
    if (_isDisposed || _userRequestedDisconnect) return;
    debugPrint('[ServerConn] WebSocket cerrado');
    _setState(ServerConnectionState.disconnected);
    _latestFrame = null;
    notifyListeners();
    _scheduleReconnect();
  }

  /// Reconexión con backoff exponencial: 3s → 5s → 8s → 12s → 15s (máx)
  void _scheduleReconnect() {
    if (_isDisposed || _userRequestedDisconnect || _serverIp.isEmpty) return;
    _reconnectTimer?.cancel();

    final delays = [3, 5, 8, 12, 15];
    final delayIdx = _reconnectAttempts.clamp(0, delays.length - 1);
    final seconds = delays[delayIdx];
    _reconnectAttempts++;

    debugPrint('[ServerConn] Reconectando en ${seconds}s (intento $_reconnectAttempts)...');
    _reconnectTimer = Timer(Duration(seconds: seconds), () {
      if (_isDisposed || _userRequestedDisconnect) return;
      if (_state != ServerConnectionState.connected) {
        _doConnect();
      }
    });
  }

  // ─── Comandos al servidor ─────────────────────────────────────────────────

  void sendCommand(Map<String, dynamic> cmd) {
    if (!isConnected || _channel == null) return;
    try {
      _channel!.sink.add(json.encode(cmd));
    } catch (e) {
      debugPrint('[ServerConn] Error enviando comando: $e');
    }
  }

  void changeCameraByIndex(int index) {
    sendCommand({'cmd': 'change_camera', 'index': index});
  }

  void changeCameraByUrl(String url) {
    sendCommand({'cmd': 'change_camera_url', 'url': url});
  }

  void requestCameraList() {
    sendCommand({'cmd': 'list_cameras'});
  }

  void requestHistory({int limit = 15}) {
    sendCommand({'cmd': 'get_history', 'limit': limit});
  }

  // ─── Desconexión manual ────────────────────────────────────────────────────

  Future<void> disconnect() async {
    _userRequestedDisconnect = true;
    _cleanup();
    _setState(ServerConnectionState.disconnected);
    notifyListeners();
  }

  Future<void> forgetServer() async {
    _userRequestedDisconnect = true;
    _cleanup();
    _serverIp = '';
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefIpKey);
    _setState(ServerConnectionState.disconnected);
    notifyListeners();
  }

  void _cleanup({bool cancelReconnect = true}) {
    if (cancelReconnect) _reconnectTimer?.cancel();
    _discoveryTimer?.cancel();
    _sub?.cancel();
    _sub = null;
    try {
      _channel?.sink.close(ws_status.goingAway);
    } catch (_) {}
    _channel = null;
  }

  void _setState(ServerConnectionState s) {
    _state = s;
  }

  @override
  void dispose() {
    _isDisposed = true;
    _userRequestedDisconnect = true;
    _killBackend();
    _cleanup();
    super.dispose();
  }
}
