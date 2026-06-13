import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:path/path.dart' as p;
import 'package:provider/provider.dart';
import '../../core/services/camera_manager_service.dart';
import '../../core/services/recording_service.dart';
import '../../core/services/server_connection_service.dart';
import '../../widgets/glass_container.dart';

// ─── Layouts disponibles ──────────────────────────────────────────────────────

enum GridLayout { single, pip, quad, sixthGrid }

extension GridLayoutExt on GridLayout {
  String get label {
    switch (this) {
      case GridLayout.single: return '1×1';
      case GridLayout.pip: return 'PiP';
      case GridLayout.quad: return '2×2';
      case GridLayout.sixthGrid: return '1+5';
    }
  }

  IconData get icon {
    switch (this) {
      case GridLayout.single: return Icons.crop_square;
      case GridLayout.pip: return Icons.picture_in_picture_alt;
      case GridLayout.quad: return Icons.grid_view;
      case GridLayout.sixthGrid: return Icons.view_quilt;
    }
  }
}

// ─── Tab de Cámaras ───────────────────────────────────────────────────────────

class CamerasTab extends StatefulWidget {
  const CamerasTab({super.key});

  @override
  State<CamerasTab> createState() => _CamerasTabState();
}

class _CamerasTabState extends State<CamerasTab> with TickerProviderStateMixin {
  GridLayout _layout = GridLayout.single;
  bool _showAddCamera = false;
  bool _isScanning = false;
  List<CameraSource> _scannedCameras = [];
  int _scanProgress = 0;
  int _scanTotal = 0;
  late TabController _tabController;

  // Controladores del formulario
  final _nameController = TextEditingController();
  final _urlController = TextEditingController();
  CameraSourceType _selectedType = CameraSourceType.wifi;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CameraManagerService>().initialize();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _nameController.dispose();
    _urlController.dispose();
    super.dispose();
  }

  // ─── Network Scan ─────────────────────────────────────────────────────────

  Future<void> _startNetworkScan() async {
    setState(() {
      _isScanning = true;
      _scannedCameras = [];
      _scanProgress = 0;
      _scanTotal = 1;
    });

    final mgr = context.read<CameraManagerService>();
    final found = await mgr.scanLocalNetwork(
      onProgress: (prog, total) {
        if (mounted) {
          setState(() {
            _scanProgress = prog;
            _scanTotal = total;
          });
        }
      },
    );

    if (mounted) {
      setState(() {
        _isScanning = false;
        _scannedCameras = found;
      });
    }
  }

  Future<void> _addCamera() async {
    final mgr = context.read<CameraManagerService>();
    final name = _nameController.text.trim();
    final url = _urlController.text.trim();

    if (name.isEmpty || url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nombre y URL/IP son obligatorios'), backgroundColor: Colors.red),
      );
      return;
    }

    final ok = await mgr.addNetworkCamera(
      name: name,
      url: url,
      type: _selectedType,
    );

    if (mounted) {
      _nameController.clear();
      _urlController.clear();
      setState(() => _showAddCamera = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? '✅ Cámara "$name" añadida' : '❌ No se pudo conectar a la cámara'),
          backgroundColor: ok ? Colors.teal : Colors.red,
        ),
      );
    }
  }

  // ─── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final mgr = context.watch<CameraManagerService>();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          _buildTopBar(cs, mgr),
          const SizedBox(height: 12),
          if (_showAddCamera) ...[
            _buildAddCameraPanel(cs, mgr),
            const SizedBox(height: 12),
          ],
          Expanded(child: _buildGridView(cs, mgr)),
        ],
      ),
    );
  }

  Widget _buildTopBar(ColorScheme cs, CameraManagerService mgr) {
    return GlassContainer(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      borderRadius: 8,
      child: Row(
        children: [
          Icon(Icons.videocam_rounded, color: cs.primary, size: 22),
          const SizedBox(width: 10),
          Text(
            'GESTIÓN DE CÁMARAS',
            style: GoogleFonts.jetBrainsMono(
              fontWeight: FontWeight.bold,
              color: cs.onSurface,
              fontSize: 14,
            ),
          ),
          const SizedBox(width: 24),
          Text(
            '${mgr.cameras.length} CÁMARA(S)  •  ${mgr.cameras.where((c) => c.isOnline).length} EN LÍNEA',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: cs.onSurfaceVariant,
            ),
          ),
          const Spacer(),
          // Layout switcher
          ...GridLayout.values.map((layout) => Padding(
            padding: const EdgeInsets.only(left: 4),
            child: Tooltip(
              message: layout.label,
              child: IconButton(
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                icon: Icon(
                  layout.icon,
                  color: _layout == layout ? cs.primary : cs.onSurfaceVariant,
                ),
                onPressed: () => setState(() => _layout = layout),
                style: IconButton.styleFrom(
                  backgroundColor: _layout == layout
                      ? cs.primary.withValues(alpha: 0.15)
                      : Colors.transparent,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                ),
              ),
            ),
          )),
          const SizedBox(width: 12),
          // Escanear red
          OutlinedButton.icon(
            icon: Icon(_isScanning ? Icons.hourglass_top : Icons.wifi_find, size: 16),
            label: Text(
              _isScanning ? 'Escaneando...' : 'ESCANEAR RED',
              style: GoogleFonts.jetBrainsMono(fontSize: 11),
            ),
            onPressed: _isScanning ? null : _startNetworkScan,
            style: OutlinedButton.styleFrom(
              foregroundColor: cs.secondary,
              side: BorderSide(color: cs.secondary.withValues(alpha: 0.5)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            ),
          ),
          const SizedBox(width: 8),
          // Añadir cámara
          FilledButton.icon(
            icon: Icon(_showAddCamera ? Icons.close : Icons.add, size: 16),
            label: Text(
              _showAddCamera ? 'CANCELAR' : 'AÑADIR CÁMARA',
              style: GoogleFonts.jetBrainsMono(fontSize: 11),
            ),
            onPressed: () => setState(() => _showAddCamera = !_showAddCamera),
            style: FilledButton.styleFrom(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAddCameraPanel(ColorScheme cs, CameraManagerService mgr) {
    return GlassContainer(
      padding: const EdgeInsets.all(16),
      borderRadius: 8,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Tabs: Manual / Descubiertas
          TabBar(
            controller: _tabController,
            labelStyle: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, fontSize: 12),
            unselectedLabelStyle: GoogleFonts.jetBrainsMono(fontSize: 12),
            tabs: const [
              Tab(text: 'AÑADIR MANUAL'),
              Tab(text: 'CÁMARAS DESCUBIERTAS'),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 180,
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildManualForm(cs),
                _buildDiscoveredList(cs, mgr),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 250.ms).slideY(begin: -0.05, end: 0);
  }

  Widget _buildManualForm(ColorScheme cs) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Nombre
        Expanded(
          flex: 2,
          child: TextField(
            controller: _nameController,
            style: GoogleFonts.jetBrainsMono(fontSize: 13),
            decoration: InputDecoration(
              labelText: 'Nombre de la cámara',
              labelStyle: TextStyle(color: cs.onSurfaceVariant, fontSize: 12),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6)),
              isDense: true,
              prefixIcon: const Icon(Icons.label_outline, size: 18),
            ),
          ),
        ),
        const SizedBox(width: 12),
        // URL / IP
        Expanded(
          flex: 3,
          child: TextField(
            controller: _urlController,
            style: GoogleFonts.jetBrainsMono(fontSize: 13),
            decoration: InputDecoration(
              labelText: 'URL / IP (ej: 192.168.1.50:554 o rtsp://...)',
              labelStyle: TextStyle(color: cs.onSurfaceVariant, fontSize: 12),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6)),
              isDense: true,
              prefixIcon: const Icon(Icons.link, size: 18),
            ),
          ),
        ),
        const SizedBox(width: 12),
        // Tipo
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('TIPO', style: GoogleFonts.jetBrainsMono(fontSize: 10, color: cs.onSurfaceVariant)),
            const SizedBox(height: 4),
            DropdownButton<CameraSourceType>(
              value: _selectedType,
              underline: const SizedBox(),
              dropdownColor: cs.surfaceContainerHigh,
              items: [
                CameraSourceType.wifi,
                CameraSourceType.bluetooth,
                CameraSourceType.rtsp,
                CameraSourceType.http,
              ].map((t) => DropdownMenuItem(
                value: t,
                child: Row(
                  children: [
                    Text(t.typeIcon, style: const TextStyle(fontSize: 16)),
                    const SizedBox(width: 6),
                    Text(t.typeLabel, style: GoogleFonts.jetBrainsMono(fontSize: 12)),
                  ],
                ),
              )).toList(),
              onChanged: (v) { if (v != null) setState(() => _selectedType = v); },
            ),
          ],
        ),
        const SizedBox(width: 12),
        // Botón añadir
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: FilledButton.icon(
            icon: const Icon(Icons.add_circle_outline, size: 18),
            label: Text('AÑADIR', style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, fontSize: 12)),
            onPressed: _addCamera,
            style: FilledButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6))),
          ),
        ),
      ],
    );
  }

  Widget _buildDiscoveredList(ColorScheme cs, CameraManagerService mgr) {
    if (_isScanning) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          LinearProgressIndicator(
            value: _scanTotal > 0 ? _scanProgress / _scanTotal : null,
          ),
          const SizedBox(height: 8),
          Text(
            'Escaneando red local... $_scanProgress / $_scanTotal',
            style: GoogleFonts.jetBrainsMono(fontSize: 12, color: cs.onSurfaceVariant),
          ),
        ],
      );
    }

    if (_scannedCameras.isEmpty) {
      return Center(
        child: Text(
          'Presiona "ESCANEAR RED" para buscar cámaras en tu red local',
          style: GoogleFonts.jetBrainsMono(fontSize: 12, color: cs.onSurfaceVariant),
          textAlign: TextAlign.center,
        ),
      );
    }

    return ListView.builder(
      itemCount: _scannedCameras.length,
      itemBuilder: (ctx, i) {
        final cam = _scannedCameras[i];
        return ListTile(
          dense: true,
          leading: Text(cam.typeIcon, style: const TextStyle(fontSize: 20)),
          title: Text(cam.name, style: GoogleFonts.jetBrainsMono(fontSize: 12)),
          subtitle: Text(cam.address, style: GoogleFonts.jetBrainsMono(fontSize: 10, color: cs.onSurfaceVariant)),
          trailing: FilledButton(
            onPressed: () async {
              await mgr.addNetworkCamera(name: cam.name, url: cam.address, type: cam.type);
              setState(() => _scannedCameras.removeAt(i));
            },
            style: FilledButton.styleFrom(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            ),
            child: Text('AÑADIR', style: GoogleFonts.jetBrainsMono(fontSize: 11)),
          ),
        );
      },
    );
  }

  // ─── Grid de cámaras ──────────────────────────────────────────────────────

  Widget _buildGridView(ColorScheme cs, CameraManagerService mgr) {
    final cams = mgr.cameras;
    if (cams.isEmpty) {
      return GlassContainer(
        borderRadius: 8,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.videocam_off_outlined, size: 64, color: cs.primary.withValues(alpha: 0.2)),
              const SizedBox(height: 16),
              Text(
                'No hay cámaras configuradas',
                style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 16),
              ),
              const SizedBox(height: 8),
              Text(
                'Añade una cámara USB, WiFi, Bluetooth o RTSP',
                style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 12),
              ),
            ],
          ),
        ),
      );
    }

    switch (_layout) {
      case GridLayout.single:
        final active = mgr.activeCamera ?? cams.first;
        return Column(
          children: [
            Expanded(child: _CameraCell(camera: active, isMain: true)),
            const SizedBox(height: 8),
            _buildCameraList(cs, mgr, cams),
          ],
        );

      case GridLayout.pip:
        return Stack(
          children: [
            _CameraCell(camera: mgr.activeCamera ?? cams.first, isMain: true),
            if (cams.length > 1)
              Positioned(
                right: 16, bottom: 16,
                width: 240, height: 135,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: _CameraCell(camera: cams[1], isMain: false),
                ),
              ),
          ],
        );

      case GridLayout.quad:
        final gridCams = cams.take(4).toList();
        return GridView.count(
          crossAxisCount: 2,
          childAspectRatio: 16 / 9,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          children: gridCams.map((c) => _CameraCell(camera: c, isMain: c.id == mgr.activeCamera?.id)).toList(),
        );

      case GridLayout.sixthGrid:
        if (cams.isEmpty) return const SizedBox();
        final main = mgr.activeCamera ?? cams.first;
        final others = cams.where((c) => c.id != main.id).take(5).toList();
        return Row(
          children: [
            Expanded(flex: 3, child: _CameraCell(camera: main, isMain: true)),
            const SizedBox(width: 8),
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  ...others.map((c) => Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: _CameraCell(camera: c, isMain: false),
                    ),
                  )),
                ],
              ),
            ),
          ],
        );
    }
  }

  Widget _buildCameraList(ColorScheme cs, CameraManagerService mgr, List<CameraSource> cams) {
    return GlassContainer(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      borderRadius: 8,
      height: 70,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: cams.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (ctx, i) {
          final cam = cams[i];
          final isActive = cam.id == mgr.activeCamera?.id;
          return GestureDetector(
            onTap: () {
              mgr.setActiveCamera(cam.id);
              final serverSvc = context.read<ServerConnectionService>();
              if (cam.type == CameraSourceType.usb) {
                final idx = int.tryParse(cam.address) ?? 0;
                serverSvc.changeCameraByIndex(idx);
              } else {
                serverSvc.changeCameraByUrl(cam.address);
              }
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                content: Text('Cambiando cámara en servidor a: ${cam.name}'),
                backgroundColor: cs.primary,
                duration: const Duration(seconds: 2),
              ));
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 160,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: isActive ? cs.primary.withValues(alpha: 0.15) : cs.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: isActive ? cs.primary : cs.outline.withValues(alpha: 0.3),
                  width: isActive ? 1.5 : 0.5,
                ),
              ),
              child: Row(
                children: [
                  Text(cam.typeIcon, style: const TextStyle(fontSize: 18)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          cam.name,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 10,
                            fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                            color: isActive ? cs.primary : cs.onSurface,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Row(
                          children: [
                            Container(
                              width: 6, height: 6,
                              decoration: BoxDecoration(
                                color: cam.isOnline ? Colors.greenAccent : Colors.red,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              cam.isOnline ? 'EN LÍNEA' : 'OFFLINE',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 9,
                                color: cam.isOnline ? Colors.greenAccent : Colors.red,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  // Botón eliminar (no USB)
                  if (cam.isNetwork)
                    GestureDetector(
                      onTap: () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (_) => AlertDialog(
                            title: const Text('¿Eliminar cámara?'),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('No')),
                              TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Sí')),
                            ],
                          ),
                        );
                        if (confirm == true && mounted) mgr.removeCamera(cam.id);
                      },
                      child: Icon(Icons.close, size: 14, color: cs.onSurfaceVariant),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

// ─── Celda de cámara individual ───────────────────────────────────────────────

class _CameraCell extends StatefulWidget {
  final CameraSource camera;
  final bool isMain;

  const _CameraCell({required this.camera, required this.isMain});

  @override
  State<_CameraCell> createState() => _CameraCellState();
}

class _CameraCellState extends State<_CameraCell> {
  Uint8List? _frame;
  bool _isSnapping = false;
  double _zoom = 1.0;
  bool _isPaused = false;
  Uint8List? _frozenFrame;

  @override
  void initState() {
    super.initState();
  }

  Future<void> _takeSnapshot() async {
    if (_isSnapping) return;
    setState(() => _isSnapping = true);
    final svc = context.read<RecordingService>();
    final path = _frame != null
        ? await svc.takeSnapshotFromBytes(_frame!)
        : await svc.takeSnapshot(context.read<ServerConnectionService>());
    if (mounted) {
      setState(() => _isSnapping = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(path != null ? '📸 Captura guardada: ${p.basename(path)}' : '❌ Error al guardar captura'),
        backgroundColor: path != null ? Colors.teal : Colors.red,
        duration: const Duration(seconds: 3),
      ));
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final cam = widget.camera;
    final rec = context.watch<RecordingService>();

    return GlassContainer(
      padding: EdgeInsets.zero,
      borderRadius: 8,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Feed de video
            _buildFeed(cs, cam),

            // Paused indicator overlay
            if (_isPaused)
              Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: Colors.redAccent, width: 1),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.pause, color: Colors.redAccent, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        'PAUSADO',
                        style: GoogleFonts.shareTechMono(color: Colors.redAccent, fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),

            // Overlay: nombre + estado
            Positioned(
              top: 8, left: 8,
              child: IgnorePointer(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(cam.typeIcon, style: const TextStyle(fontSize: 12)),
                      const SizedBox(width: 4),
                      Text(
                        cam.name.length > 18 ? '${cam.name.substring(0, 16)}…' : cam.name,
                        style: GoogleFonts.shareTechMono(color: Colors.white70, fontSize: 11),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        width: 6, height: 6,
                        decoration: BoxDecoration(
                          color: cam.isOnline ? Colors.greenAccent : Colors.red,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // IA badge
            if (cam.hasAi)
              Positioned(
                top: 8, right: 8,
                child: IgnorePointer(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.greenAccent.withValues(alpha: 0.2),
                      border: Border.all(color: Colors.greenAccent, width: 0.5),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text('IA ACTIVA', style: GoogleFonts.shareTechMono(fontSize: 9, color: Colors.greenAccent)),
                  ),
                ),
              ),

            // Controles hover (captura, grabar, pausa, zoom)
            Positioned(
              bottom: 8, right: 8,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Zoom in
                  _overlayBtn(
                    Icons.zoom_in,
                    () => setState(() => _zoom = (_zoom + 0.25).clamp(1.0, 4.0)),
                    cs,
                  ),
                  const SizedBox(width: 4),
                  // Zoom out
                  _overlayBtn(
                    Icons.zoom_out,
                    () => setState(() => _zoom = (_zoom - 0.25).clamp(1.0, 4.0)),
                    cs,
                  ),
                  const SizedBox(width: 4),
                  // Pause / Play stream
                  if (cam.hasAi) ...[
                    _overlayBtn(
                      _isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                      () => setState(() => _isPaused = !_isPaused),
                      cs,
                      iconColor: _isPaused ? Colors.greenAccent : Colors.white70,
                    ),
                    const SizedBox(width: 4),
                  ],
                  // Snapshot
                  _overlayBtn(
                    _isSnapping ? Icons.hourglass_top : Icons.camera_alt_outlined,
                    _takeSnapshot,
                    cs,
                  ),
                  // Grabar / Detener grabación
                  if (cam.hasAi) ...[
                    const SizedBox(width: 4),
                    _overlayBtn(
                      rec.isRecording ? Icons.stop_circle_outlined : Icons.fiber_manual_record,
                      () async {
                        if (rec.isRecording) {
                          final path = await rec.stopRecording();
                          if (mounted && path != null) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                              content: Text('🎬 Grabación guardada: ${p.basename(path)}'),
                              backgroundColor: Colors.teal[700],
                              duration: const Duration(seconds: 5),
                            ));
                          }
                        } else {
                          final serverSvc = context.read<ServerConnectionService>();
                          await rec.startRecording(serverSvc);
                        }
                      },
                      cs,
                      iconColor: rec.isRecording ? Colors.redAccent : Colors.white70,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFeed(ColorScheme cs, CameraSource cam) {
    if (!cam.isOnline) {
      return Container(
        color: Colors.black,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.signal_wifi_connected_no_internet_4, size: 48, color: Colors.red.withValues(alpha: 0.5)),
              const SizedBox(height: 8),
              Text('OFFLINE', style: GoogleFonts.shareTechMono(color: Colors.red.withValues(alpha: 0.5), fontSize: 14)),
            ],
          ),
        ),
      );
    }

    if (cam.hasAi) {
      // Feed en tiempo real recibido desde el Servidor IA por WebSocket
      return Consumer<ServerConnectionService>(
        builder: (context, serverSvc, _) {
          final frame = serverSvc.latestFrame;
          if (frame != null) {
            if (!_isPaused) {
              _frame = frame; // Guardar para snapshot
              _frozenFrame = frame;
            }
            final displayFrame = _isPaused ? _frozenFrame : frame;
            if (displayFrame != null) {
              return ClipRect(
                child: OverflowBox(
                  maxWidth: double.infinity,
                  maxHeight: double.infinity,
                  child: Transform.scale(
                    scale: _zoom,
                    child: Image.memory(displayFrame, fit: BoxFit.cover, gaplessPlayback: true),
                  ),
                ),
              );
            }
          }
          return Container(
            color: const Color(0xFF0A0E1A),
            child: Center(
              child: CircularProgressIndicator(color: cs.primary),
            ),
          );
        },
      );
    }

    // Cámara de red o USB inactiva: mostrar placeholder con info y botón de abrir
    return Container(
      color: const Color(0xFF0A0F1E),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(cam.type == CameraSourceType.usb ? Icons.videocam : Icons.stream, size: 48, color: cs.primary.withValues(alpha: 0.4)),
            const SizedBox(height: 8),
            Text(
              cam.name.toUpperCase(),
              style: GoogleFonts.shareTechMono(fontSize: 12, color: cs.primary.withValues(alpha: 0.6)),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              cam.isNetwork 
                  ? (cam.address.length > 40 ? '${cam.address.substring(0, 37)}…' : cam.address)
                  : 'CÁMARA LOCAL PUERTO USB ${cam.address}',
              style: GoogleFonts.shareTechMono(fontSize: 10, color: Colors.white38),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              icon: const Icon(Icons.play_arrow, size: 16),
              label: Text('ABRIR CON IA', style: GoogleFonts.jetBrainsMono(fontSize: 11)),
              onPressed: () {
                final serverSvc = context.read<ServerConnectionService>();
                if (cam.type == CameraSourceType.usb) {
                  final idx = int.tryParse(cam.address) ?? 0;
                  serverSvc.changeCameraByIndex(idx);
                } else {
                  serverSvc.changeCameraByUrl(cam.address);
                }
                final mgr = context.read<CameraManagerService>();
                mgr.setActiveCamera(cam.id);
                
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text('Cambiando cámara en servidor a: ${cam.name}'),
                  backgroundColor: cs.primary,
                  duration: const Duration(seconds: 2),
                ));
              },
              style: OutlinedButton.styleFrom(
                foregroundColor: cs.primary,
                side: BorderSide(color: cs.primary.withValues(alpha: 0.5)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _overlayBtn(IconData icon, VoidCallback onTap, ColorScheme cs, {Color? iconColor}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 32, height: 32,
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: cs.primary.withValues(alpha: 0.2)),
        ),
        child: Icon(icon, size: 16, color: iconColor ?? Colors.white70),
      ),
    );
  }
}
