import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';
import 'server_connection_service.dart';

/// Modelo para una grabación guardada
class VideoRecording {
  final String path;
  final String filename;
  final DateTime createdAt;
  final int durationSeconds;
  final int fileSizeBytes;

  const VideoRecording({
    required this.path,
    required this.filename,
    required this.createdAt,
    required this.durationSeconds,
    required this.fileSizeBytes,
  });
}

/// Servicio de grabación de video de ultra-bajo consumo.
///
/// Estrategia: acumula frames JPEG que Python ya genera en disco
/// y usa ffmpeg para ensamblarlos en MP4 al finalizar la grabación.
/// No duplica el procesamiento de video — casi cero overhead de CPU/RAM.
class RecordingService extends ChangeNotifier {
  bool _isRecording = false;
  bool _hasFfmpeg = false;
  String _saveDirectory = '';
  List<String> _frameBuffer = []; // rutas temporales de frames capturados
  Timer? _captureTimer;
  Timer? _durationTimer;
  int _elapsedSeconds = 0;
  String? _tempDir;
  List<VideoRecording> _recordings = [];
  String _status = 'Listo';

  bool get isRecording => _isRecording;
  bool get hasFfmpeg => _hasFfmpeg;
  String get saveDirectory => _saveDirectory;
  int get elapsedSeconds => _elapsedSeconds;
  List<VideoRecording> get recordings => List.unmodifiable(_recordings);
  String get status => _status;
  String get elapsedFormatted {
    final m = (_elapsedSeconds ~/ 60).toString().padLeft(2, '0');
    final s = (_elapsedSeconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }


  Future<void> initialize() async {
    // Detectar ffmpeg
    try {
      final res = await Process.run('ffmpeg', ['-version']).timeout(const Duration(seconds: 3));
      _hasFfmpeg = res.exitCode == 0;
    } catch (_) {
      _hasFfmpeg = false;
    }

    // Cargar carpeta personalizada desde SharedPreferences o usar predeterminada
    final prefs = await SharedPreferences.getInstance();
    final customDir = prefs.getString('recording_save_dir');
    
    if (customDir != null && Directory(customDir).existsSync()) {
      _saveDirectory = customDir;
    } else {
      final userProfile = Platform.environment['USERPROFILE'] ?? '';
      final videosDir = Directory(p.join(userProfile, 'Videos', 'AlertaVecinal'));
      if (!videosDir.existsSync()) videosDir.createSync(recursive: true);
      _saveDirectory = videosDir.path;
    }

    // Cargar grabaciones existentes
    await _scanRecordings();
    notifyListeners();
  }

  Future<void> setSaveDirectory(String dir) async {
    _saveDirectory = dir;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('recording_save_dir', dir);
    await _scanRecordings();
    notifyListeners();
  }

  Future<void> startRecording(ServerConnectionService serverService) async {
    if (_isRecording) return;

    // Crear directorio temporal para los frames
    final tmpBase = p.join(_saveDirectory, '.tmp_frames_${DateTime.now().millisecondsSinceEpoch}');
    await Directory(tmpBase).create(recursive: true);
    _tempDir = tmpBase;
    _frameBuffer.clear();
    _elapsedSeconds = 0;
    _isRecording = true;
    _status = 'Grabando...';

    // Capturar frame en memoria cada ~66ms (≈15fps escritura)
    int frameIndex = 0;
    _captureTimer = Timer.periodic(const Duration(milliseconds: 67), (_) async {
      try {
        final frameBytes = serverService.latestFrame;
        if (frameBytes != null) {
          final dst = p.join(_tempDir!, 'frame_${frameIndex.toString().padLeft(6, '0')}.jpg');
          await File(dst).writeAsBytes(frameBytes);
          _frameBuffer.add(dst);
          frameIndex++;
        }
      } catch (_) {}
    });

    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _elapsedSeconds++;
      notifyListeners();
    });

    notifyListeners();
  }

  Future<String?> stopRecording() async {
    if (!_isRecording) return null;

    _captureTimer?.cancel();
    _durationTimer?.cancel();
    _isRecording = false;
    _status = 'Procesando video...';
    notifyListeners();

    if (_frameBuffer.isEmpty) {
      _status = 'Sin frames capturados';
      notifyListeners();
      return null;
    }

    final timestamp = DateTime.now();
    final filename = 'grabacion_${timestamp.year}${timestamp.month.toString().padLeft(2,'0')}${timestamp.day.toString().padLeft(2,'0')}_${timestamp.hour.toString().padLeft(2,'0')}${timestamp.minute.toString().padLeft(2,'0')}${timestamp.second.toString().padLeft(2,'0')}.mp4';
    final outputPath = p.join(_saveDirectory, filename);

    String? result;

    if (_hasFfmpeg && _frameBuffer.isNotEmpty) {
      result = await _encodeWithFfmpeg(outputPath, timestamp);
    } else {
      // Fallback: guardar el último frame como imagen estática si no hay ffmpeg
      result = await _saveFallback(outputPath, timestamp);
    }

    // Limpiar frames temporales
    try {
      if (_tempDir != null) {
        await Directory(_tempDir!).delete(recursive: true);
      }
    } catch (_) {}
    _tempDir = null;
    _frameBuffer.clear();
    _status = result != null ? 'Guardado: $filename' : 'Error al guardar';
    await _scanRecordings();
    notifyListeners();
    return result;
  }

  Future<String?> _encodeWithFfmpeg(String outputPath, DateTime ts) async {
    try {
      final framePattern = p.join(_tempDir!, 'frame_%06d.jpg');
      final args = [
        '-y',
        '-framerate', '15',
        '-i', framePattern,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',   // Mínimo CPU en encoding
        '-crf', '28',             // Calidad balanceada
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        outputPath,
      ];
      final res = await Process.run('ffmpeg', args).timeout(const Duration(minutes: 5));
      if (res.exitCode == 0 && File(outputPath).existsSync()) {
        return outputPath;
      }
      debugPrint('[RecordingService] ffmpeg error: ${res.stderr}');
      return null;
    } catch (e) {
      debugPrint('[RecordingService] ffmpeg exception: $e');
      return null;
    }
  }

  Future<String?> _saveFallback(String outputPath, DateTime ts) async {
    // Sin ffmpeg: guardar último frame como JPEG
    try {
      final jpgPath = outputPath.replaceAll('.mp4', '_captura.jpg');
      if (_frameBuffer.isNotEmpty) {
        await File(_frameBuffer.last).copy(jpgPath);
        return jpgPath;
      }
    } catch (_) {}
    return null;
  }

  /// Tomar captura instantánea del frame actual desde el servidor IA
  Future<String?> takeSnapshot(ServerConnectionService serverService, {String? customDir}) async {
    try {
      final bytes = serverService.latestFrame;
      if (bytes == null) return null;

      final dir = customDir ?? _saveDirectory;
      await Directory(dir).create(recursive: true);

      final ts = DateTime.now();
      final filename = 'captura_${ts.year}${ts.month.toString().padLeft(2,'0')}${ts.day.toString().padLeft(2,'0')}_${ts.hour.toString().padLeft(2,'0')}${ts.minute.toString().padLeft(2,'0')}${ts.second.toString().padLeft(2,'0')}.jpg';
      final dst = p.join(dir, filename);
      await File(dst).writeAsBytes(bytes);
      return dst;
    } catch (e) {
      debugPrint('[RecordingService] snapshot error: $e');
      return null;
    }
  }

  /// Tomar captura de un frame en bytes directamente
  Future<String?> takeSnapshotFromBytes(Uint8List bytes, {String? customDir}) async {
    try {
      final dir = customDir ?? _saveDirectory;
      await Directory(dir).create(recursive: true);
      final ts = DateTime.now();
      final filename = 'captura_${ts.year}${ts.month.toString().padLeft(2,'0')}${ts.day.toString().padLeft(2,'0')}_${ts.hour.toString().padLeft(2,'0')}${ts.minute.toString().padLeft(2,'0')}${ts.second.toString().padLeft(2,'0')}.jpg';
      final dst = p.join(dir, filename);
      await File(dst).writeAsBytes(bytes);
      return dst;
    } catch (_) {
      return null;
    }
  }

  Future<void> _scanRecordings() async {
    try {
      final dir = Directory(_saveDirectory);
      if (!dir.existsSync()) return;
      final files = dir.listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.mp4') || f.path.endsWith('.jpg'))
        .where((f) => !p.basename(f.path).startsWith('.'))
        .toList();
      files.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
      _recordings = files.take(50).map((f) {
        final stat = f.statSync();
        return VideoRecording(
          path: f.path,
          filename: p.basename(f.path),
          createdAt: stat.modified,
          durationSeconds: 0,
          fileSizeBytes: stat.size,
        );
      }).toList();
    } catch (_) {}
  }

  Future<void> deleteRecording(String path) async {
    try {
      await File(path).delete();
      await _scanRecordings();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> openRecordingFolder() async {
    if (Platform.isWindows) {
      await Process.run('explorer', [_saveDirectory]);
    }
  }

  @override
  void dispose() {
    _captureTimer?.cancel();
    _durationTimer?.cancel();
    super.dispose();
  }
}
