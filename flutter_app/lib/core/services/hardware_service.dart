import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';

/// Servicio de hardware — Monitor de recursos de la PC cliente local.
///
/// En la arquitectura Cliente-Servidor, este servicio ya NO arranca ni
/// controla el proceso de Python IA (eso lo hace servidor_ia.py en el servidor).
/// Solo monitorea el consumo de la PC local del cliente (CPU, RAM) para
/// mostrar los indicadores del Dashboard.
///
/// El cambio de cámara se hace ahora a través de ServerConnectionService.
class HardwareService extends ChangeNotifier {
  String cpuUsage = '0%';
  String ramUsage = '0 MB';
  String gpuUsage = 'N/A';
  bool isPolling = false;
  Timer? _timer;

  bool _hasNvidiaGpu = true;
  bool _isFetching = false;

  // Lista de cámaras y cámara activa (ahora son solo metadatos visuales
  // — la cámara real la controla el servidor)
  int currentCamera = 0;
  List<Map<String, dynamic>> availableCameras = [
    {'index': 0, 'name': 'Cámara Predeterminada'}
  ];

  Future<void> initialize() async {
    startPolling();
    await _detectCameras();
  }

  // ─── Detección de cámaras con WMI ────────────────────────────────────────

  Future<void> _detectCameras() async {
    try {
      if (Platform.isWindows) {
        const command =
            r"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object -ExpandProperty Caption";
        final res = await Process.run('powershell', ['-Command', command])
            .timeout(const Duration(seconds: 5));

        if (res.exitCode == 0 && res.stdout.toString().trim().isNotEmpty) {
          final lines = res.stdout.toString().trim().split('\n');
          final seenNames = <String>{};
          availableCameras.clear();
          int camIndex = 0;
          for (final line in lines) {
            final name = line.trim().replaceAll('\r', '');
            if (name.isEmpty ||
                name.toLowerCase().contains('virtual') ||
                seenNames.contains(name)) {
              continue;
            }
            seenNames.add(name);
            availableCameras.add({'index': camIndex, 'name': name});
            camIndex++;
          }
        }
      }

      if (availableCameras.isEmpty) {
        availableCameras.add({'index': 0, 'name': 'Cámara Predeterminada'});
      }

      if (availableCameras.isNotEmpty) {
        currentCamera = availableCameras.first['index'] as int;
      }
      notifyListeners();
    } catch (e) {
      debugPrint('Error detectando cámaras: $e');
    }
  }

  // ─── Cambio de cámara ─────────────────────────────────────────────────────
  //
  // NOTA: El cambio real de cámara se hace a través de ServerConnectionService.
  // Aquí solo actualizamos el estado visual local.

  void updateCurrentCamera(int index) {
    currentCamera = index;
    notifyListeners();
  }

  // ─── Polling de Hardware (recursos de la PC cliente) ─────────────────────

  void startPolling() {
    if (isPolling) return;
    isPolling = true;
    _fetchHardwareData();
    // 12 segundos — suficiente para mostrar datos útiles sin saturar PowerShell
    _timer = Timer.periodic(
        const Duration(seconds: 12), (_) => _fetchHardwareData());
  }

  void stopPolling() {
    isPolling = false;
    _timer?.cancel();
  }

  Future<void> _fetchHardwareData() async {
    if (!Platform.isWindows || _isFetching) return;
    _isFetching = true;

    try {
      final pidDart = pid;
      final command =
          r' $cpu=(Get-CimInstance Win32_Processor|Measure-Object -Property LoadPercentage -Average).Average;'
          ' \$mSelf=(Get-Process -Id $pidDart -EA SilentlyContinue).WorkingSet64;'
          ' \$ram=\$mSelf/1MB;'
          ' @{cpu=\$cpu;ram=\$ram}|ConvertTo-Json -Compress';
      final cmd = command.replaceAll(r'$pidDart', pidDart.toString());

      final res = await Process.run(
              'powershell', ['-NoProfile', '-NonInteractive', '-Command', cmd])
          .timeout(const Duration(seconds: 10));

      if (res.exitCode == 0 && res.stdout.toString().trim().isNotEmpty) {
        try {
          // ignore: avoid_dynamic_calls
          final data = (res.stdout.toString().trim());
          // Parse manual simple para evitar dart:convert overhead
          final cpuMatch = RegExp(r'"cpu"\s*:\s*([\d.]+)').firstMatch(data);
          final ramMatch = RegExp(r'"ram"\s*:\s*([\d.]+)').firstMatch(data);
          if (cpuMatch != null) {
            cpuUsage = '${double.tryParse(cpuMatch.group(1) ?? '0')?.toStringAsFixed(0) ?? '?'}%';
          }
          if (ramMatch != null) {
            final ramMb = double.tryParse(ramMatch.group(1) ?? '0') ?? 0;
            ramUsage = ramMb >= 1024
                ? '${(ramMb / 1024).toStringAsFixed(1)} GB'
                : '${ramMb.toStringAsFixed(0)} MB';
          }
        } catch (_) {}
      }

      // GPU (solo si Nvidia)
      if (_hasNvidiaGpu) {
        try {
          final gpuRes = await Process.run('nvidia-smi', [
            '--query-gpu=utilization.gpu',
            '--format=csv,noheader,nounits'
          ]).timeout(const Duration(seconds: 3));
          if (gpuRes.exitCode == 0 &&
              gpuRes.stdout.toString().trim().isNotEmpty) {
            gpuUsage = '${gpuRes.stdout.toString().trim().split('\n').first}%';
          } else {
            _hasNvidiaGpu = false;
            gpuUsage = 'N/A';
          }
        } catch (_) {
          _hasNvidiaGpu = false;
          gpuUsage = 'N/A';
        }
      }

      notifyListeners();
    } catch (e) {
      debugPrint('[HW] fetch error: $e');
    } finally {
      _isFetching = false;
    }
  }

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }
}
