import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:path/path.dart' as p;
import 'package:provider/provider.dart';
import 'package:file_selector/file_selector.dart';
import '../../core/services/recording_service.dart';
import '../../widgets/glass_container.dart';

class RecordingsTab extends StatefulWidget {
  const RecordingsTab({super.key});

  @override
  State<RecordingsTab> createState() => _RecordingsTabState();
}

class _RecordingsTabState extends State<RecordingsTab> {
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final svc = context.watch<RecordingService>();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header bar
          GlassContainer(
            height: 64,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            borderRadius: 8,
            child: Row(
              children: [
                Icon(Icons.video_library_rounded, color: cs.primary, size: 24),
                const SizedBox(width: 12),
                Text(
                  'GRABACIONES Y CAPTURAS',
                  style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, color: cs.onSurface, fontSize: 14),
                ),
                const SizedBox(width: 16),
                Text(
                  '${svc.recordings.length} ARCHIVOS',
                  style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 11),
                ),
                const Spacer(),
                // Carpeta de guardado actual
                Tooltip(
                  message: 'Carpeta de guardado: ${svc.saveDirectory}',
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.folder_open, size: 16),
                    label: Text(
                      p.basename(svc.saveDirectory).toUpperCase(),
                      style: GoogleFonts.jetBrainsMono(fontSize: 11),
                    ),
                    onPressed: () => svc.openRecordingFolder(),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: cs.secondary,
                      side: BorderSide(color: cs.secondary.withValues(alpha: 0.5)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Tooltip(
                  message: 'Cambiar carpeta de guardado',
                  child: OutlinedButton(
                    onPressed: () async {
                      final String? result = await getDirectoryPath(
                        confirmButtonText: 'Seleccionar Carpeta',
                      );
                      if (result != null) {
                        await svc.setSaveDirectory(result);
                      }
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: cs.secondary,
                      side: BorderSide(color: cs.secondary.withValues(alpha: 0.5)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                    ),
                    child: const Icon(Icons.edit_location_alt, size: 16),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text('ACTUALIZAR', style: GoogleFonts.jetBrainsMono(fontSize: 11)),
                  onPressed: () => setState(() {}),
                  style: FilledButton.styleFrom(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          // Lista de archivos
          Expanded(
            child: GlassContainer(
              padding: EdgeInsets.zero,
              borderRadius: 8,
              child: svc.recordings.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.videocam_off, size: 64, color: cs.primary.withValues(alpha: 0.15)),
                          const SizedBox(height: 16),
                          Text(
                            'No hay grabaciones todavía',
                            style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 14),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Usa el botón ● REC en la pantalla principal para grabar',
                            style: GoogleFonts.jetBrainsMono(color: cs.onSurfaceVariant, fontSize: 11),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: svc.recordings.length,
                      itemBuilder: (ctx, i) {
                        final rec = svc.recordings[i];
                        return _RecordingTile(
                          recording: rec,
                          onDelete: () => svc.deleteRecording(rec.path),
                        ).animate().fadeIn(delay: Duration(milliseconds: i * 30), duration: 300.ms);
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecordingTile extends StatelessWidget {
  final VideoRecording recording;
  final VoidCallback onDelete;

  const _RecordingTile({required this.recording, required this.onDelete});

  bool get isVideo => recording.filename.endsWith('.mp4');

  String get _sizeStr {
    final kb = recording.fileSizeBytes / 1024;
    if (kb < 1024) return '${kb.toStringAsFixed(0)} KB';
    return '${(kb / 1024).toStringAsFixed(1)} MB';
  }

  String get _dateStr {
    final d = recording.createdAt;
    return '${d.day.toString().padLeft(2,'0')}/${d.month.toString().padLeft(2,'0')}/${d.year}  '
        '${d.hour.toString().padLeft(2,'0')}:${d.minute.toString().padLeft(2,'0')}:${d.second.toString().padLeft(2,'0')}';
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHigh.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: cs.outline.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: isVideo ? cs.primary.withValues(alpha: 0.15) : cs.secondary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(
              isVideo ? Icons.movie_outlined : Icons.image_outlined,
              color: isVideo ? cs.primary : cs.secondary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  recording.filename,
                  style: GoogleFonts.jetBrainsMono(
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                    color: cs.onSurface,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  '$_dateStr  •  $_sizeStr',
                  style: GoogleFonts.jetBrainsMono(fontSize: 10, color: cs.onSurfaceVariant),
                ),
              ],
            ),
          ),
          // Abrir archivo
          IconButton(
            icon: const Icon(Icons.open_in_new, size: 18),
            tooltip: 'Abrir archivo',
            onPressed: () async {
              await Process.run('explorer', [recording.path]);
            },
          ),
          // Abrir carpeta contenedora
          IconButton(
            icon: const Icon(Icons.folder_open, size: 18),
            tooltip: 'Abrir carpeta',
            onPressed: () async {
              await Process.run('explorer', ['/select,', recording.path]);
            },
          ),
          // Eliminar
          IconButton(
            icon: Icon(Icons.delete_outline, size: 18, color: cs.error),
            tooltip: 'Eliminar',
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  backgroundColor: const Color(0xFF0D1117),
                  title: Text('¿Eliminar?', style: GoogleFonts.jetBrainsMono(color: Colors.white, fontWeight: FontWeight.bold)),
                  content: Text(recording.filename, style: GoogleFonts.jetBrainsMono(color: Colors.white70, fontSize: 12)),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCELAR')),
                    TextButton(onPressed: () => Navigator.pop(context, true), child: Text('ELIMINAR', style: TextStyle(color: cs.error))),
                  ],
                ),
              );
              if (ok == true) onDelete();
            },
          ),
        ],
      ),
    );
  }
}
