import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';

class CameraService extends ChangeNotifier {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _isInitialized = false;
  String _errorMsg = '';
  CameraDescription? _selectedCamera;

  CameraController? get controller => _controller;
  List<CameraDescription> get cameras => _cameras;
  bool get isInitialized => _isInitialized;
  String get errorMsg => _errorMsg;
  CameraDescription? get selectedCamera => _selectedCamera;

  Future<void> initialize() async {
    _isInitialized = true; // Fingir que está inicializado
    notifyListeners();
  }

  Future<void> selectCamera(CameraDescription camera) async {
    // No hacer nada
  }

  @override
  void dispose() {
    super.dispose();
  }
}
