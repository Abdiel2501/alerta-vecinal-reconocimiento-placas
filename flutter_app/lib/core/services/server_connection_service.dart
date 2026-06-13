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
  discovering,  // Buscando el servidor en la red local con mDNS
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
/// Responsabilidades:
///  - Guardar/recuperar la IP del servidor desde SharedPreferences.
///  - Auto-descubrir el servidor en la red local (escaneando /health en la LAN).
///  - Mantener la conexión WebSocket activa con reconexión automática.
///  - Decodificar frames JPEG de Base64 → Uint8List y notificar a la UI.
///  - Recibir y acumular alertas de placas robadas.
///  - Enviar comandos (cambio de cámara, etc.) al servidor.
class ServerConnectionService extends ChangeNotifier {
  // ── Estado ─────────────────────────────────────────────────────────────────
  ServerConnectionState _state = ServerConnectionState.disconnected;
  String _serverIp = '';
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
  List<Map<String, dynamic>> get availableCameras => List.unmodifiable(_availableCameras);
  List<ServerAlert> get alerts => List.unmodifiable(_alerts);
  Uint8List? get latestFrame => _latestFrame;
  bool get isConnected => _state == ServerConnectionState.connected;

  // ─── Inicialización ────────────────────────────────────────────────────────

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _serverIp = prefs.getString(_prefIpKey) ?? '';
    _serverPort = prefs.getInt(_prefPortKey) ?? 8765;

    if (_serverIp.isNotEmpty) {
      // IP guardada — conectar directamente
      await connect(_serverIp, port: _serverPort);
    } else {
      // Sin IP guardada — arrancar descubrimiento automático
      await discoverServer();
    }
  }

  // ─── Auto-descubrimiento en LAN ───────────────────────────────────────────

  /// Escanea la red local buscando el servidor IA por el endpoint /health.
  /// No requiere que el usuario escriba la IP.
  Future<void> discoverServer() async {
    _setState(ServerConnectionState.discovering);
    _errorMessage = 'Buscando servidor en la red local...';
    notifyListeners();

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

    debugPrint('[ServerConn] Escaneando subnet: $subnet.0/24 en puerto $_serverPort');

    // Escanear en paralelo todos los hosts de la subred
    final futures = <Future>[];
    for (int i = 1; i <= 254; i++) {
      final host = '$subnet.$i';
      futures.add(_checkHost(host));
    }

    // También intentar localhost por si server corre en la misma PC
    futures.add(_checkHost('127.0.0.1'));
    futures.add(_checkHost('localhost'));

    // Ejecutar en batches de 30 para no colapsar la red
    for (int i = 0; i < futures.length; i += 30) {
      final batch = futures.sublist(i, (i + 30).clamp(0, futures.length));
      await Future.wait(batch);
      if (_state == ServerConnectionState.connected) return; // Ya conectó
    }

    // No encontró servidor
    if (_state != ServerConnectionState.connected) {
      _setState(ServerConnectionState.error);
      _errorMessage = 'No se encontró el Servidor IA en la red local.\nVerifica que el servidor esté encendido.';
      notifyListeners();
    }
  }

  Future<void> _checkHost(String host) async {
    if (_state == ServerConnectionState.connected) return;
    try {
      final url = 'http://$host:$_serverPort/health';
      final request = await HttpClient()
          .getUrl(Uri.parse(url))
          .timeout(const Duration(milliseconds: 400));
      final response = await request.close().timeout(const Duration(milliseconds: 400));
      if (response.statusCode == 200) {
        debugPrint('[ServerConn] ✅ Servidor encontrado en $host');
        await connect(host, port: _serverPort, saveIp: true);
      }
    } catch (_) {}
  }

  // ─── Conexión WebSocket ────────────────────────────────────────────────────

  Future<void> connect(String ip, {int? port, bool saveIp = true}) async {
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

    await _doConnect();
  }

  Future<void> _doConnect() async {
    _cleanup();

    final uri = Uri.parse('ws://$_serverIp:$_serverPort/ws');
    debugPrint('[ServerConn] Conectando a $uri');

    try {
      _channel = WebSocketChannel.connect(uri);
      await _channel!.ready.timeout(const Duration(seconds: 5));

      _setState(ServerConnectionState.connected);
      _errorMessage = '';
      notifyListeners();

      debugPrint('[ServerConn] ✅ Conectado al servidor IA');

      _sub = _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('[ServerConn] Error al conectar: $e');
      _onError(e);
    }
  }

  void _onMessage(dynamic raw) {
    try {
      final Map<String, dynamic> msg = json.decode(raw as String);
      final type = msg['type'] as String?;

      switch (type) {
        case 'frame':
          final b64 = msg['data'] as String?;
          if (b64 != null && b64.isNotEmpty) {
            _latestFrame = base64Decode(b64);
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
          break; // keep-alive, ignorar

        default:
          break;
      }
    } catch (e) {
      debugPrint('[ServerConn] Error parseando mensaje: $e');
    }
  }

  void _onError(dynamic error) {
    debugPrint('[ServerConn] Error WebSocket: $error');
    _setState(ServerConnectionState.error);
    _errorMessage = 'Error de conexión: $error';
    _latestFrame = null;
    notifyListeners();
    _scheduleReconnect();
  }

  void _onDone() {
    debugPrint('[ServerConn] WebSocket cerrado');
    if (_userRequestedDisconnect) return;
    _setState(ServerConnectionState.disconnected);
    _latestFrame = null;
    notifyListeners();
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_userRequestedDisconnect || _serverIp.isEmpty) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (_state != ServerConnectionState.connected && !_userRequestedDisconnect) {
        debugPrint('[ServerConn] Reconectando...');
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

  /// Cambia la cámara activa en el servidor
  void changeCameraByIndex(int index) {
    sendCommand({'cmd': 'change_camera', 'index': index});
  }

  /// Cambia a una cámara de red (RTSP/HTTP)
  void changeCameraByUrl(String url) {
    sendCommand({'cmd': 'change_camera_url', 'url': url});
  }

  /// Solicita la lista de cámaras disponibles en el servidor
  void requestCameraList() {
    sendCommand({'cmd': 'list_cameras'});
  }

  /// Solicita el historial de alertas recientes
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

  /// Cambia de servidor (olvida la IP guardada y redescubre)
  Future<void> forgetServer() async {
    _userRequestedDisconnect = true;
    _cleanup();
    _serverIp = '';
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefIpKey);
    _setState(ServerConnectionState.disconnected);
    notifyListeners();
  }

  void _cleanup() {
    _reconnectTimer?.cancel();
    _discoveryTimer?.cancel();
    _sub?.cancel();
    _sub = null;
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
  }

  void _setState(ServerConnectionState s) {
    _state = s;
  }

  @override
  void dispose() {
    _userRequestedDisconnect = true;
    _cleanup();
    super.dispose();
  }
}
