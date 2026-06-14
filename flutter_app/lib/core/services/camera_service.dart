import 'package:flutter/foundation.dart';

/// Servicio de cámara (stub) — La app recibe vídeo vía WebSocket desde el
/// servidor Python. Este servicio no usa directamente el hardware de cámara;
/// el acceso físico lo gestiona OpenCV en el servidor IA.
class CameraService extends ChangeNotifier {
  bool _isInitialized = false;
  String _errorMsg = '';

  bool get isInitialized => _isInitialized;
  String get errorMsg => _errorMsg;

  Future<void> initialize() async {
    _isInitialized = true;
    notifyListeners();
  }

  @override
  void dispose() {
    super.dispose();
  }
}
