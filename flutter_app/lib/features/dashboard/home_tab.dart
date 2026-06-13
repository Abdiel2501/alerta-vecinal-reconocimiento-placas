import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:path/path.dart' as p;
import '../../core/services/camera_service.dart';
import '../../core/services/hardware_service.dart';
import '../../core/services/recording_service.dart';
import '../../core/services/ai_database_service.dart';
import '../../core/services/server_connection_service.dart';
import '../../core/localization/app_localizations.dart';
import '../../widgets/glass_container.dart';
import 'package:file_selector/file_selector.dart';

class HomeTab extends StatefulWidget {
  const HomeTab({super.key});

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final CameraService _cameraService = CameraService();
  String _timeString = '';
  String _cctvTimeString = '';
  Timer? _timer;
  Timer? _aiDbTimer;
  List<AiAlert> _aiAlerts = [];



  @override
  void initState() {
    super.initState();
    _cameraService.initialize().then((_) => setState(() {}));
    _cameraService.addListener(() => setState(() {}));

    _timer = Timer.periodic(const Duration(milliseconds: 100), (t) => _getTime());
    _getTime();

    // Escuchar frames y alertas directamente desde el ServerConnectionService
    // (llegan por WebSocket desde el servidor IA — sin leer disco)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RecordingService>().initialize();

      final serverSvc = context.read<ServerConnectionService>();
      serverSvc.addListener(_onServerUpdate);

      // Si hay alertas históricas ya cargadas, mostrarlas
      _syncAlertsFromServer(serverSvc);
    });
  }

  void _onServerUpdate() {
    if (!mounted) return;
    final svc = context.read<ServerConnectionService>();
    _syncAlertsFromServer(svc);
  }

  void _syncAlertsFromServer(ServerConnectionService svc) {
    if (!mounted) return;
    final newAlerts = svc.alerts.map((a) => AiAlert(
      id: a.trackId,
      placaDetectada: a.placa,
      placaBd: a.placaBd,
      similitud: a.similitud / 100.0,
      rutaFotoVehiculo: a.fotoVehiculoPath ?? '',
      rutaFotoPlaca: a.fotoPlacaPath ?? '',
      fechaAlerta: a.timestamp.toIso8601String(),
    )).toList();
    if (newAlerts.length != _aiAlerts.length) {
      setState(() => _aiAlerts = newAlerts);
    }
  }



  Future<void> _exportToCsv() async {
    try {
      final allAlerts = await AiDatabaseService.getRecentAlerts(limit: 5000);

      final ts = DateTime.now();
      final fname = 'alertas_anpr_${ts.year}${ts.month.toString().padLeft(2,'0')}${ts.day.toString().padLeft(2,'0')}.csv';

      final FileSaveLocation? result = await getSaveLocation(
        suggestedName: fname,
        acceptedTypeGroups: [
          XTypeGroup(label: 'CSV', extensions: ['csv']),
        ],
      );

      if (result == null) return;

      final buf = StringBuffer();
      buf.write('\uFEFF'); // BOM para Excel
      buf.writeln('ID,Fecha/Hora,Placa Detectada,Placa BD Coincidencia,Similitud %');

      for (final alert in allAlerts) {
        buf.writeln(
          '${alert.id},'
          '"${alert.fechaAlerta}",'
          '"${alert.placaDetectada}",'
          '"${alert.placaBd}",'
          '"${(alert.similitud * 100).toStringAsFixed(1)}%"',
        );
      }

      final Uint8List fileData = Uint8List.fromList(utf8.encode(buf.toString()));
      final XFile textFile = XFile.fromData(fileData, mimeType: 'text/csv', name: fname);
      await textFile.saveTo(result.path);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ CSV exportado: $fname (${allAlerts.length} registros)'),
          backgroundColor: Colors.teal[700],
          duration: const Duration(seconds: 4),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('❌ Error al exportar: $e'),
          backgroundColor: Colors.red[800],
          duration: const Duration(seconds: 4),
        ));
      }
    }
  }

  void _getTime() {
    final now = DateTime.now();
    final ms = (now.millisecond / 10).round().toString().padLeft(2, '0');
    setState(() {
      _timeString = '${now.hour.toString().padLeft(2,'0')}:${now.minute.toString().padLeft(2,'0')}:${now.second.toString().padLeft(2,'0')} ${now.year}-${now.month.toString().padLeft(2,'0')}-${now.day.toString().padLeft(2,'0')}';
      _cctvTimeString = '${now.year}-${now.month.toString().padLeft(2,'0')}-${now.day.toString().padLeft(2,'0')} ${now.hour.toString().padLeft(2,'0')}:${now.minute.toString().padLeft(2,'0')}:${now.second.toString().padLeft(2,'0')}.$ms';
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _aiDbTimer?.cancel();
    _cameraService.dispose();
    try {
      context.read<ServerConnectionService>().removeListener(_onServerUpdate);
    } catch (_) {}
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          _buildTopKpiBar(colorScheme),
          const SizedBox(height: 16),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 7,
                  child: Column(
                    children: [
                      Expanded(
                        flex: 6,
                        child: _buildLiveVideo(colorScheme),
                      ),
                      const SizedBox(height: 16),
                      Expanded(
                        flex: 4,
                        child: _buildDataGrid(colorScheme),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 3,
                  child: _buildTicker(colorScheme),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── Top KPI Bar ─────────────────────────────────────────────────────────

  Widget _buildTopKpiBar(ColorScheme colorScheme) {
    return GlassContainer(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      borderRadius: 8,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _buildPill(colorScheme, 'TELEGRAM', 'CONNECTED', colorScheme.secondary),
            const SizedBox(width: 24),
            // Indicador del servidor IA (refleja el estado real de la conexión WebSocket)
            Consumer<ServerConnectionService>(
              builder: (context, svc, _) {
                final label = switch (svc.state) {
                  ServerConnectionState.connected => 'SERVIDOR: ONLINE',
                  ServerConnectionState.connecting => 'SERVIDOR: CONECTANDO',
                  ServerConnectionState.discovering => 'SERVIDOR: BUSCANDO',
                  ServerConnectionState.error => 'SERVIDOR: ERROR',
                  ServerConnectionState.disconnected => 'SERVIDOR: OFFLINE',
                };
                final color = svc.isConnected ? Colors.greenAccent : colorScheme.error;
                return _buildPill(colorScheme, label,
                    svc.isConnected ? '${svc.fps.toStringAsFixed(0)} FPS · ${svc.clientsCount} CL' : '---',
                    color);
              },
            ),
            const SizedBox(width: 24),
            Consumer<HardwareService>(
              builder: (context, hw, _) => Text(
                'CPU: ${hw.cpuUsage}  GPU: ${hw.gpuUsage}  RAM: ${hw.ramUsage}',
                style: GoogleFonts.jetBrainsMono(color: colorScheme.primary, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
            const SizedBox(width: 24),
            Text(
              _timeString,
              style: GoogleFonts.jetBrainsMono(color: colorScheme.onSurface, fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPill(ColorScheme cs, String label, String status, Color statusColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHigh,
        border: Border.all(color: cs.outlineVariant),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$label: ', style: GoogleFonts.jetBrainsMono(fontSize: 11, color: cs.onSurfaceVariant)),
          Text(status, style: GoogleFonts.jetBrainsMono(fontSize: 11, color: statusColor, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  // ─── Live Video ──────────────────────────────────────────────────────────

  Widget _buildLiveVideo(ColorScheme cs) {
    return GlassContainer(
      width: double.infinity,
      padding: EdgeInsets.zero,
      borderRadius: 8,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Stack(
          alignment: Alignment.center,
          fit: StackFit.expand,
          children: [
            // Feed principal de Python
            // Feed principal de Python por WebSocket
            Consumer<ServerConnectionService>(
              builder: (context, serverSvc, _) {
                final frame = serverSvc.latestFrame;
                if (frame != null) {
                  return Image.memory(frame, fit: BoxFit.cover, gaplessPlayback: true);
                }
                return Container(
                  color: const Color(0xFF0A0E1A),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Stack(
                          alignment: Alignment.topRight,
                          children: [
                            Icon(
                              Icons.videocam_rounded,
                              size: 96,
                              color: Colors.white.withValues(alpha: 0.08),
                            ),
                            Container(
                              margin: const EdgeInsets.only(top: 10, right: 6),
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                color: Colors.redAccent,
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(color: Colors.redAccent.withValues(alpha: 0.8), blurRadius: 12, spreadRadius: 3),
                                ],
                              ),
                            ).animate(onPlay: (c) => c.repeat(reverse: true))
                             .fade(begin: 0.15, end: 1.0, duration: 700.ms),
                          ],
                        ),
                        const SizedBox(height: 20),
                        Text(
                          'Conectando cámara...',
                          style: GoogleFonts.inter(
                            color: Colors.white30,
                            fontSize: 14,
                            letterSpacing: 1.5,
                          ),
                        ).animate(onPlay: (c) => c.repeat(reverse: true))
                         .fade(begin: 0.3, end: 0.8, duration: 1200.ms),
                      ],
                    ),
                  ),
                );
              },
            ),

            // Crosshair
            IgnorePointer(
              child: Center(
                child: Icon(Icons.add, size: 100, color: Colors.greenAccent.withValues(alpha: 0.2)),
              ),
            ),

            // HUD superior izquierda: REC blink + info
            Positioned(
              top: 16, left: 16,
              child: IgnorePointer(
                child: MediaQuery(
                  data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
                  child: Consumer<RecordingService>(
                    builder: (ctx, rec, _) => Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 10, height: 10,
                              decoration: BoxDecoration(
                                color: rec.isRecording ? Colors.red : Colors.red.withValues(alpha: 0.4),
                                shape: BoxShape.circle,
                                boxShadow: rec.isRecording
                                    ? [const BoxShadow(color: Colors.redAccent, blurRadius: 8, spreadRadius: 2)]
                                    : [],
                              ),
                            )
                            .animate(onPlay: (c) => c.repeat(reverse: true))
                            .fade(begin: 0.3, end: 1.0, duration: 800.ms),
                            const SizedBox(width: 8),
                            Text(
                              rec.isRecording ? 'REC ${rec.elapsedFormatted}' : 'REC',
                              style: GoogleFonts.shareTechMono(
                                color: rec.isRecording ? Colors.yellowAccent : Colors.redAccent.withValues(alpha: 0.6),
                                fontWeight: FontWeight.bold,
                                fontSize: 16, // slightly larger for visibility
                                letterSpacing: 1.5,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'CAM 01 — MULTI-LANE ANPR',
                          style: GoogleFonts.shareTechMono(color: Colors.white70, fontSize: 12),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'FPS: 15   BITRATE: 2.4 Mbps   LIVE',
                          style: GoogleFonts.shareTechMono(color: Colors.white54, fontSize: 10),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // Selector de cámara (top right)
            // Selector de cámara — envía el comando al servidor IA por WebSocket
            Positioned(
              top: 16, right: 16,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: cs.primary.withValues(alpha: 0.3)),
                ),
                child: Consumer<ServerConnectionService>(
                  builder: (ctx, serverSvc, _) {
                    final cams = serverSvc.availableCameras;
                    if (cams.isEmpty) return const SizedBox.shrink();
                    final currentIdx = cams.indexWhere((c) =>
                        c['name'].toString() == serverSvc.currentCamera ||
                        c['index'].toString() == serverSvc.currentCamera);
                    final safeVal = currentIdx >= 0
                        ? cams[currentIdx]['index'] as int
                        : cams.first['index'] as int;
                    return DropdownButton<int>(
                      value: safeVal,
                      dropdownColor: Colors.black87,
                      underline: const SizedBox(),
                      icon: Icon(Icons.videocam, color: cs.primary, size: 20),
                      items: cams.map((camMap) {
                        final val = camMap['index'] as int;
                        final name = camMap['name'] as String;
                        final displayName = name.length > 25
                            ? '${name.substring(0, 22)}...'
                            : name;
                        return DropdownMenuItem<int>(
                          value: val,
                          child: Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: Text(
                              displayName.toUpperCase(),
                              style: GoogleFonts.shareTechMono(
                                  color: Colors.white70, fontSize: 12),
                            ),
                          ),
                        );
                      }).toList(),
                      onChanged: (newValue) {
                        if (newValue != null) {
                          // Enviar comando al servidor IA (no reinicia nada local)
                          serverSvc.changeCameraByIndex(newValue);
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                            content: Text('Cambiando cámara en servidor...'),
                            backgroundColor: cs.primary,
                            duration: const Duration(seconds: 2),
                          ));
                        }
                      },
                    );
                  },
                ),
              ),
            ),

            // Timestamp (bottom left)
            Positioned(
              bottom: 16, left: 16,
              child: IgnorePointer(
                child: MediaQuery(
                  data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
                  child: Text(
                    _cctvTimeString,
                    style: GoogleFonts.shareTechMono(
                      color: Colors.yellowAccent,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      shadows: [const Shadow(blurRadius: 4, color: Colors.black54, offset: Offset(1, 1))],
                    ),
                  ),
                ),
              ),
            ),

            // Controles de acción (bottom right): Captura + Grabar
            Positioned(
              bottom: 16, right: 16,
              child: MediaQuery(
                data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
                child: Consumer<RecordingService>(
                  builder: (ctx, rec, _) => Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Botón Captura
                      _VideoControlBtn(
                        icon: Icons.camera_alt_outlined,
                        label: 'CAPTURA',
                        color: cs.secondary,
                        onTap: () async {
                          final serverSvc = context.read<ServerConnectionService>();
                          final frameBytes = serverSvc.latestFrame;
                          String? path;
                          if (frameBytes != null) {
                            path = await rec.takeSnapshotFromBytes(frameBytes);
                          } else {
                            path = await rec.takeSnapshot(serverSvc);
                          }
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                              content: Text(path != null
                                  ? '📸 ${p.basename(path)}'
                                  : '❌ Error al guardar captura'),
                              backgroundColor: path != null ? Colors.teal[700] : Colors.red[800],
                              duration: const Duration(seconds: 3),
                            ));
                          }
                        },
                      ),
                      const SizedBox(width: 8),
                      // Botón Grabar / Detener
                      _VideoControlBtn(
                        icon: rec.isRecording ? Icons.stop_circle_outlined : Icons.fiber_manual_record,
                        label: rec.isRecording ? 'DETENER ${rec.elapsedFormatted}' : 'GRABAR',
                        color: rec.isRecording ? Colors.red : cs.primary,
                        onTap: () async {
                          if (rec.isRecording) {
                            final path = await rec.stopRecording();
                            if (mounted && path != null) {
                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                                content: Text('🎬 Guardado: ${p.basename(path)}'),
                                backgroundColor: Colors.teal[700],
                                duration: const Duration(seconds: 5),
                              ));
                            }
                          } else {
                            final serverSvc = context.read<ServerConnectionService>();
                            await rec.startRecording(serverSvc);
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // Status badge ANPR (bottom center)
            Positioned(
              bottom: 16,
              child: IgnorePointer(
                child: MediaQuery(
                  data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: cs.primary.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      AppLocalizations.of(context, 'analyzing_traffic').toUpperCase(),
                      style: GoogleFonts.shareTechMono(
                        color: cs.primary,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.5,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Data Grid ───────────────────────────────────────────────────────────

  Widget _buildDataGrid(ColorScheme cs) {
    return GlassContainer(
      width: double.infinity,
      padding: EdgeInsets.zero,
      borderRadius: 8,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: cs.surfaceContainerHigh,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  AppLocalizations.of(context, 'tactical_alerts_log'),
                  style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, color: cs.onSurface),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.download, size: 16),
                  label: Text(
                    AppLocalizations.of(context, 'export_csv'),
                    style: GoogleFonts.jetBrainsMono(fontSize: 12),
                  ),
                  onPressed: _exportToCsv,
                ),
              ],
            ),
          ),
          Expanded(
            child: _aiAlerts.isEmpty
                ? Center(
                    child: Text(
                      'Sin alertas todavía — La IA está monitoreando...',
                      style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 12),
                    ),
                  )
                : ListView(
                    children: [
                      DataTable(
                        headingRowHeight: 36,
                        dataRowMinHeight: 36,
                        dataRowMaxHeight: 36,
                        columns: [
                          DataColumn(label: Text(AppLocalizations.of(context, 'col_time'))),
                          DataColumn(label: Text(AppLocalizations.of(context, 'col_plate'))),
                          DataColumn(label: const Text('COINCIDENCIA')),
                          DataColumn(label: Text(AppLocalizations.of(context, 'col_confidence'))),
                          DataColumn(label: Text(AppLocalizations.of(context, 'col_status'))),
                        ],
                        rows: _aiAlerts.take(10).map((a) {
                          final colorRow = cs.errorContainer.withValues(alpha: 0.2);
                          final textColor = cs.error;
                          final dateStr = a.fechaAlerta.length > 10
                              ? a.fechaAlerta.substring(11, 19)
                              : a.fechaAlerta;
                          return DataRow(
                            color: WidgetStateProperty.all(colorRow),
                            cells: [
                              DataCell(Text(dateStr, style: TextStyle(color: textColor))),
                              DataCell(Text(a.placaDetectada, style: TextStyle(fontWeight: FontWeight.bold, color: textColor))),
                              DataCell(Text(a.placaBd, style: TextStyle(color: textColor))),
                              DataCell(Text('${(a.similitud * 100).toStringAsFixed(1)}%', style: TextStyle(color: textColor))),
                              DataCell(Text('ALERTA BD', style: TextStyle(color: textColor))),
                            ],
                          );
                        }).toList(),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  // ─── Ticker ──────────────────────────────────────────────────────────────

  Widget _buildTicker(ColorScheme cs) {
    return GlassContainer(
      padding: EdgeInsets.zero,
      borderRadius: 8,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: cs.surfaceContainerHigh,
              border: Border(bottom: BorderSide(color: cs.outline)),
            ),
            child: Text(
              AppLocalizations.of(context, 'recent_captures'),
              style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, color: cs.onSurface),
              textAlign: TextAlign.center,
            ),
          ),
          Expanded(
            child: _aiAlerts.isEmpty
                ? Center(
                    child: Icon(Icons.notifications_none, size: 48, color: cs.primary.withValues(alpha: 0.2)),
                  )
                : ListView.builder(
                    itemCount: _aiAlerts.length,
                    itemBuilder: (context, index) {
                      final alerta = _aiAlerts[index];
                      return Container(
                        margin: const EdgeInsets.all(8),
                        decoration: BoxDecoration(border: Border.all(color: cs.outlineVariant)),
                        child: Column(
                          children: [
                            Container(
                              height: 120, // Aumentado para ver mejor el auto
                              width: double.infinity,
                              color: Colors.black87,
                              child: Stack(
                                fit: StackFit.expand,
                                children: [
                                  if (alerta.rutaFotoVehiculo.isNotEmpty && File(alerta.rutaFotoVehiculo).existsSync())
                                    Image.file(
                                      File(alerta.rutaFotoVehiculo),
                                      fit: BoxFit.cover,
                                    ),
                                  Center(
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      color: Colors.black54,
                                      child: Text(
                                        alerta.placaDetectada,
                                        style: GoogleFonts.jetBrainsMono(
                                          fontSize: 24,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.redAccent,
                                          letterSpacing: 4,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.all(4),
                              color: cs.surfaceContainerHigh,
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    'ROBADO (${alerta.placaBd})',
                                    style: GoogleFonts.jetBrainsMono(fontSize: 10, color: cs.error),
                                  ),
                                  Text(
                                    '${(alerta.similitud * 100).toStringAsFixed(1)}%',
                                    style: GoogleFonts.jetBrainsMono(fontSize: 10, color: cs.onSurfaceVariant),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ─── Botón de control de video overlay ───────────────────────────────────────

class _VideoControlBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _VideoControlBtn({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.6)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: GoogleFonts.shareTechMono(color: color, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }
}
