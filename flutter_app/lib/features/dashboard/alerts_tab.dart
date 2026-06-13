import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:path/path.dart' as p;
import 'dart:io';
import '../../core/services/ai_database_service.dart';
import '../../widgets/glass_container.dart';

class AlertsTab extends StatefulWidget {
  const AlertsTab({super.key});

  @override
  State<AlertsTab> createState() => _AlertsTabState();
}

class _AlertsTabState extends State<AlertsTab> {
  List<AiAlert> _history = [];
  bool _isLoading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _loadHistory();
    // Actualizar historial cada 3 segundos automáticamente para tiempo real
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _loadHistory());
  }

  Future<void> _loadHistory() async {
    try {
      final alerts = await AiDatabaseService.getRecentAlerts(limit: 50);
      if (mounted) {
        setState(() {
          _history = alerts;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _clearHistory() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF0D1117),
        title: Text(
          '¿BORRAR HISTORIAL?',
          style: GoogleFonts.jetBrainsMono(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        content: Text(
          'Esta acción eliminará todos los registros del historial permanentemente en la base de datos de la IA.',
          style: GoogleFonts.jetBrainsMono(color: Colors.white70, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('CANCELAR', style: GoogleFonts.jetBrainsMono(color: Colors.white54, fontSize: 12)),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text('ELIMINAR TODO', style: GoogleFonts.jetBrainsMono(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 12)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final success = await AiDatabaseService.clearAlertsHistory();
      if (success) {
        _loadHistory();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Historial de alertas eliminado correctamente.'),
              backgroundColor: Colors.redAccent,
            ),
          );
        }
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // HEADER BAR
          GlassContainer(
            height: 64,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            borderRadius: 8,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.history, color: colorScheme.primary, size: 24),
                    const SizedBox(width: 12),
                    Text(
                      'HISTORIAL DE ALERTAS TÁCTICAS',
                      style: GoogleFonts.jetBrainsMono(
                        color: colorScheme.onSurface,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
                if (_history.isNotEmpty)
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.redAccent.withValues(alpha: 0.15),
                      foregroundColor: Colors.redAccent,
                      side: const BorderSide(color: Colors.redAccent),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    icon: const Icon(Icons.delete_forever, size: 18),
                    label: Text(
                      'BORRAR HISTORIAL',
                      style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                    onPressed: _clearHistory,
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          // MAIN BODY
          Expanded(
            child: GlassContainer(
              padding: EdgeInsets.zero,
              borderRadius: 8,
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _history.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.notifications_none, size: 64, color: colorScheme.primary.withValues(alpha: 0.2)),
                              const SizedBox(height: 16),
                              Text(
                                'No se han registrado alertas en el sistema todavía.',
                                style: GoogleFonts.jetBrainsMono(color: colorScheme.onSurfaceVariant, fontSize: 14),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _history.length,
                          itemBuilder: (context, index) {
                            final alert = _history[index];
                            final time = alert.fechaAlerta.length > 18 ? alert.fechaAlerta.substring(11, 19) : alert.fechaAlerta;
                            final date = alert.fechaAlerta.length > 10 ? alert.fechaAlerta.substring(0, 10) : '';
                            return Container(
                              margin: const EdgeInsets.only(bottom: 12),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: colorScheme.errorContainer.withValues(alpha: 0.08),
                                border: Border.all(color: colorScheme.error.withValues(alpha: 0.25)),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: colorScheme.error.withValues(alpha: 0.15),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      alert.placaDetectada,
                                      style: GoogleFonts.shareTechMono(
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                        color: colorScheme.error,
                                        letterSpacing: 2,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'VEHÍCULO REPORTADO COMO ROBADO',
                                          style: GoogleFonts.jetBrainsMono(
                                            color: colorScheme.error,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 12,
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Coincidencia BD: ${alert.placaBd} | Similitud: ${(alert.similitud * 100).toStringAsFixed(1)}%',
                                          style: GoogleFonts.jetBrainsMono(
                                            color: colorScheme.onSurfaceVariant,
                                            fontSize: 11,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        time,
                                        style: GoogleFonts.jetBrainsMono(
                                          color: colorScheme.onSurface,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        date,
                                        style: GoogleFonts.jetBrainsMono(
                                          color: colorScheme.onSurfaceVariant,
                                          fontSize: 10,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
            ),
          ),
        ],
      ),
    );
  }
}
