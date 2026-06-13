import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Tipos de fuente de cámara soportados por el sistema
enum CameraSourceType {
  usb,       // Cámara USB local (OpenCV index)
  bluetooth, // Cámara Bluetooth (RTSP/HTTP stream)
  wifi,      // Cámara IP WiFi (RTSP/HTTP stream)
  rtsp,      // Stream RTSP genérico
  http,      // Cámara HTTP MJPEG
  app,       // App YI IOT y otras apps
}

/// Extensión de utilidades sobre el enum CameraSourceType
extension CameraSourceTypeX on CameraSourceType {
  String get typeLabel {
    switch (this) {
      case CameraSourceType.usb: return 'USB';
      case CameraSourceType.bluetooth: return 'BT';
      case CameraSourceType.wifi: return 'WiFi';
      case CameraSourceType.rtsp: return 'RTSP';
      case CameraSourceType.http: return 'HTTP';
      case CameraSourceType.app: return 'APP';
    }
  }

  String get typeIcon {
    switch (this) {
      case CameraSourceType.usb: return '🖥️';
      case CameraSourceType.bluetooth: return '🔵';
      case CameraSourceType.wifi: return '📶';
      case CameraSourceType.rtsp: return '📡';
      case CameraSourceType.http: return '🌐';
      case CameraSourceType.app: return '📱';
    }
  }

  bool get isNetworkType => this != CameraSourceType.usb;
}

/// Modelo de una cámara en el sistema
class CameraSource {
  final String id;
  final String name;
  final CameraSourceType type;
  final String address; // Para USB: índice numérico como String. Para IP: URL completa
  bool isOnline;
  bool hasAi; // ¿Tiene la IA de Python activa?
  String? lastError;
  DateTime? lastSeen;

  CameraSource({
    required this.id,
    required this.name,
    required this.type,
    required this.address,
    this.isOnline = false,
    this.hasAi = false,
    this.lastError,
    this.lastSeen,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'type': type.index,
    'address': address,
    'hasAi': hasAi,
  };

  factory CameraSource.fromJson(Map<String, dynamic> j) => CameraSource(
    id: j['id'] as String,
    name: j['name'] as String,
    type: CameraSourceType.values[j['type'] as int],
    address: j['address'] as String,
    hasAi: j['hasAi'] as bool? ?? false,
  );

  String get typeLabel {
    switch (type) {
      case CameraSourceType.usb: return 'USB';
      case CameraSourceType.bluetooth: return 'BT';
      case CameraSourceType.wifi: return 'WiFi';
      case CameraSourceType.rtsp: return 'RTSP';
      case CameraSourceType.http: return 'HTTP';
      case CameraSourceType.app: return 'APP';
    }
  }

  String get typeIcon {
    switch (type) {
      case CameraSourceType.usb: return '🖥️';
      case CameraSourceType.bluetooth: return '🔵';
      case CameraSourceType.wifi: return '📶';
      case CameraSourceType.rtsp: return '📡';
      case CameraSourceType.http: return '🌐';
      case CameraSourceType.app: return '📱';
    }
  }

  bool get isNetwork => type != CameraSourceType.usb;
}

/// Servicio central de gestión de cámaras.
///
/// Combina:
/// - Cámaras USB detectadas automáticamente por WMI/CIM (Windows)
/// - Cámaras IP/WiFi/Bluetooth añadidas manualmente por el usuario
/// - Escaneo de red local para descubrir cámaras IP automáticamente
/// - Verificación de conectividad periódica
class CameraManagerService extends ChangeNotifier {
  final List<CameraSource> _cameras = [];
  String _activeCameraId = '';
  bool _isScanning = false;
  Timer? _pingTimer;
  static const String _prefsKey = 'cam_manager_sources';

  List<CameraSource> get cameras => List.unmodifiable(_cameras);
  CameraSource? get activeCamera => _cameras.isEmpty
      ? null
      : _cameras.firstWhere((c) => c.id == _activeCameraId, orElse: () => _cameras.first);
  bool get isScanning => _isScanning;

  Future<void> initialize() async {
    await _loadSaved();
    await _detectUsbCameras();
    _startPingTimer();
    notifyListeners();
  }

  // ─── Cámaras USB Locales ─────────────────────────────────────────────────

  Future<void> _detectUsbCameras() async {
    if (!Platform.isWindows) return;
    try {
      final cmd = r"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object -ExpandProperty Caption";
      final res = await Process.run('powershell', ['-Command', cmd])
          .timeout(const Duration(seconds: 5));

      if (res.exitCode == 0 && res.stdout.toString().trim().isNotEmpty) {
        final lines = res.stdout.toString().trim().split('\n');
        int usbIndex = 0;
        final seenNames = <String>{};

        // Eliminar USB y App previas para re-escanear
        _cameras.removeWhere((c) => c.type == CameraSourceType.usb || c.type == CameraSourceType.app);

        for (final line in lines) {
          final name = line.trim().replaceAll('\r', '');
          if (name.isEmpty || name.toLowerCase().contains('virtual') || seenNames.contains(name)) continue;
          seenNames.add(name);
          _cameras.insert(usbIndex, CameraSource(
            id: 'usb_$usbIndex',
            name: name,
            type: CameraSourceType.usb,
            address: usbIndex.toString(),
            isOnline: true,
            lastSeen: DateTime.now(),
          ));
          usbIndex++;
        }
      }

      // Si no se encontraron, agregar la genérica
      if (_cameras.where((c) => c.type == CameraSourceType.usb).isEmpty) {
        _cameras.insert(0, CameraSource(
          id: 'usb_0',
          name: 'Cámara Predeterminada',
          type: CameraSourceType.usb,
          address: '0',
          isOnline: true,
        ));
      }

      if (_activeCameraId.isEmpty && _cameras.isNotEmpty) {
        _activeCameraId = _cameras.first.id;
        _cameras.first.hasAi = true;
      }

      // Agregar siempre la cámara de la App YI IOT
      _cameras.insert(0, CameraSource(
        id: 'app_yi_iot',
        name: 'App Oficial YI IOT',
        type: CameraSourceType.app,
        address: 'pantalla',
        isOnline: true,
      ));

    } catch (e) {
      debugPrint('[CameraManager] USB detection error: $e');
    }
  }

  // ─── Añadir Cámaras de Red (WiFi / Bluetooth / RTSP / HTTP) ─────────────

  /// Añade una cámara de red manualmente
  Future<bool> addNetworkCamera({
    required String name,
    required String url,
    required CameraSourceType type,
  }) async {
    // Validación básica de URL
    final normalized = _normalizeUrl(url, type);
    if (normalized == null) return false;

    final id = '${type.name}_${DateTime.now().millisecondsSinceEpoch}';
    final cam = CameraSource(
      id: id,
      name: name,
      type: type,
      address: normalized,
      isOnline: false,
    );

    // Test de conectividad previo (solo para RTSP/HTTP)
    final online = await _pingCamera(cam);
    cam.isOnline = online;
    if (online) cam.lastSeen = DateTime.now();

    _cameras.add(cam);
    await _saveCameras();
    notifyListeners();
    return true;
  }

  /// Eliminar una cámara
  Future<void> removeCamera(String id) async {
    _cameras.removeWhere((c) => c.id == id);
    if (_activeCameraId == id && _cameras.isNotEmpty) {
      _activeCameraId = _cameras.first.id;
    }
    await _saveCameras();
    notifyListeners();
  }

  /// Cambiar la cámara activa (la que tiene la IA)
  Future<void> setActiveCamera(String id) async {
    for (final cam in _cameras) {
      cam.hasAi = cam.id == id;
    }
    _activeCameraId = id;
    notifyListeners();
  }

  // ─── Descubrimiento de Red ───────────────────────────────────────────────

  /// Escanea la red local en busca de cámaras IP comunes (puertos 554, 80, 8080, 8554)
  Future<List<CameraSource>> scanLocalNetwork({
    String subnet = '192.168.1',
    void Function(int progress, int total)? onProgress,
  }) async {
    _isScanning = true;
    notifyListeners();

    final found = <CameraSource>[];
    final commonPorts = [554, 8554, 80, 8080, 8000];

    // Obtener subnet local del gateway
    String localSubnet = subnet;
    try {
      final interfaces = await NetworkInterface.list();
      for (final iface in interfaces) {
        for (final addr in iface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            final parts = addr.address.split('.');
            if (parts.length == 4) {
              localSubnet = '${parts[0]}.${parts[1]}.${parts[2]}';
              break;
            }
          }
        }
      }
    } catch (_) {}

    // Escaneo paralelo de 1-254
    int scanned = 0;
    final total = 254 * commonPorts.length;
    final tasks = <Future>[];

    for (int i = 1; i <= 254; i++) {
      for (final port in commonPorts) {
        tasks.add(() async {
          final host = '$localSubnet.$i';
          try {
            final sock = await Socket.connect(host, port, timeout: const Duration(milliseconds: 300));
            await sock.close();
            // Puerto abierto — posiblemente una cámara IP
            final camType = port == 554 || port == 8554 ? CameraSourceType.rtsp : CameraSourceType.wifi;
            final url = port == 554 || port == 8554
                ? 'rtsp://$host:$port/stream'
                : 'http://$host:$port/video';
            if (!found.any((c) => c.address.contains(host))) {
              found.add(CameraSource(
                id: 'discovered_${host.replaceAll('.', '_')}_$port',
                name: 'Cámara ${camType.typeLabel} ($host:$port)',
                type: camType,
                address: url,
                isOnline: true,
                lastSeen: DateTime.now(),
              ));
            }
          } catch (_) {}
          scanned++;
          onProgress?.call(scanned, total);
        }());
      }
    }

    // Lanzar en batches de 50 para no saturar el sistema
    for (int i = 0; i < tasks.length; i += 50) {
      final batch = tasks.sublist(i, (i + 50).clamp(0, tasks.length));
      await Future.wait(batch);
    }

    _isScanning = false;
    notifyListeners();
    return found;
  }

  // ─── Ping / Verificación ─────────────────────────────────────────────────

  void _startPingTimer() {
    _pingTimer?.cancel();
    // Verificar conectividad cada 30 segundos
    _pingTimer = Timer.periodic(const Duration(seconds: 30), (_) => _pingAllCameras());
  }

  Future<void> _pingAllCameras() async {
    bool changed = false;
    for (final cam in _cameras) {
      if (cam.isNetwork) {
        final wasOnline = cam.isOnline;
        final isNowOnline = await _pingCamera(cam);
        if (wasOnline != isNowOnline) {
          cam.isOnline = isNowOnline;
          if (isNowOnline) cam.lastSeen = DateTime.now();
          changed = true;
        }
      }
    }
    if (changed) notifyListeners();
  }

  Future<bool> _pingCamera(CameraSource cam) async {
    try {
      final uri = Uri.parse(cam.address);
      final host = uri.host;
      final port = uri.port > 0 ? uri.port : (cam.type == CameraSourceType.rtsp ? 554 : 80);
      final sock = await Socket.connect(host, port, timeout: const Duration(seconds: 2));
      await sock.close();
      return true;
    } catch (_) {
      return false;
    }
  }

  // ─── Persistencia ────────────────────────────────────────────────────────

  Future<void> _saveCameras() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final networkCams = _cameras.where((c) => c.isNetwork).map((c) => c.toJson()).toList();
      await prefs.setString(_prefsKey, networkCams.toString());
      // Serialización manual
      final List<String> parts = networkCams.map((m) =>
        '${m['id']}|${m['name']}|${m['type']}|${m['address']}|${m['hasAi']}'
      ).toList();
      await prefs.setStringList('${_prefsKey}_list', parts);
    } catch (_) {}
  }

  Future<void> _loadSaved() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final parts = prefs.getStringList('${_prefsKey}_list') ?? [];
      for (final part in parts) {
        final tokens = part.split('|');
        if (tokens.length >= 5) {
          final typeIdx = int.tryParse(tokens[2]) ?? 0;
          _cameras.add(CameraSource(
            id: tokens[0],
            name: tokens[1],
            type: CameraSourceType.values[typeIdx],
            address: tokens[3],
            hasAi: tokens[4] == 'true',
          ));
        }
      }
    } catch (_) {}
  }

  // ─── Utilidades ──────────────────────────────────────────────────────────

  /// Normaliza y valida la URL de la cámara
  String? _normalizeUrl(String raw, CameraSourceType type) {
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;

    if (type == CameraSourceType.rtsp) {
      if (!trimmed.startsWith('rtsp://')) return 'rtsp://$trimmed';
      return trimmed;
    }
    if (type == CameraSourceType.http) {
      if (!trimmed.startsWith('http')) return 'http://$trimmed';
      return trimmed;
    }
    if (type == CameraSourceType.wifi || type == CameraSourceType.bluetooth) {
      // Aceptar IP directa, URL RTSP o HTTP
      if (trimmed.startsWith('rtsp://') || trimmed.startsWith('http')) return trimmed;
      return 'rtsp://$trimmed:554/stream'; // Formato por defecto
    }
    return trimmed;
  }

  /// Genera la URL del stream para abrir con OpenCV/Python
  String getStreamUrlForPython(CameraSource cam) {
    if (cam.type == CameraSourceType.usb || cam.type == CameraSourceType.app) {
      return cam.address; // Número entero o "pantalla"
    }
    return cam.address; // URL completa para RTSP/HTTP
  }

  @override
  void dispose() {
    _pingTimer?.cancel();
    super.dispose();
  }
}
