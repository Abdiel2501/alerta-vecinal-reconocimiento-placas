import 'package:flutter/material.dart';
import '../core/localization/app_localizations.dart';

class SidebarNav extends StatelessWidget {
  final int indexActual;
  final Function(int) alSeleccionar;
  final String nombreUsuario;

  const SidebarNav({
    super.key,
    required this.indexActual,
    required this.alSeleccionar,
    required this.nombreUsuario,
  });

  Widget _buildNavItem(BuildContext context, int index, IconData icon, String title, {Color? badgeColor}) {
    final isActive = indexActual == index;
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      child: InkWell(
        onTap: () => alSeleccionar(index),
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 46,
          decoration: BoxDecoration(
            color: isActive ? colorScheme.primary.withValues(alpha: 0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
            boxShadow: isActive
                ? [BoxShadow(color: colorScheme.primary.withValues(alpha: 0.25), blurRadius: 12, spreadRadius: 1)]
                : [],
          ),
          child: Row(
            children: [
              const SizedBox(width: 16),
              Stack(
                children: [
                  Icon(icon, color: isActive ? colorScheme.primary : colorScheme.onSurfaceVariant, size: 22),
                  if (badgeColor != null)
                    Positioned(
                      right: 0, top: 0,
                      child: Container(
                        width: 8, height: 8,
                        decoration: BoxDecoration(color: badgeColor, shape: BoxShape.circle),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 16),
              Text(
                title,
                style: TextStyle(
                  color: isActive ? colorScheme.onSurface : colorScheme.onSurfaceVariant,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  letterSpacing: 1,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      width: 240,
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        border: Border(right: BorderSide(color: colorScheme.outline, width: 1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Logo
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
            child: Row(
              children: [
                Icon(Icons.shield_moon, color: colorScheme.primary, size: 30),
                const SizedBox(width: 12),
                Text(
                  'ALERTA\nVECINAL',
                  style: TextStyle(
                    color: colorScheme.onSurface,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2,
                    height: 1.1,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),

          // Separador
          Divider(color: colorScheme.outline.withValues(alpha: 0.4), height: 1, indent: 20, endIndent: 20),
          const SizedBox(height: 12),

          // Sección: MONITOREO
          _buildSectionLabel(context, 'MONITOREO'),
          _buildNavItem(context, 0, Icons.dashboard_rounded, AppLocalizations.of(context, 'dashboard')),
          _buildNavItem(context, 1, Icons.grid_view_rounded, 'CÁMARAS'),

          const SizedBox(height: 8),

          // Sección: EVENTOS
          _buildSectionLabel(context, 'EVENTOS'),
          _buildNavItem(context, 2, Icons.notifications_active_rounded, AppLocalizations.of(context, 'alerts')),
          _buildNavItem(context, 3, Icons.video_library_rounded, 'GRABACIONES'),

          const SizedBox(height: 8),

          // Sección: SISTEMA
          _buildSectionLabel(context, 'SISTEMA'),
          _buildNavItem(context, 4, Icons.settings_rounded, AppLocalizations.of(context, 'settings')),

          const Spacer(),

          // Footer: usuario
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: colorScheme.outline.withValues(alpha: 0.4))),
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: colorScheme.primary.withValues(alpha: 0.2),
                  child: Icon(Icons.person, color: colorScheme.primary, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        nombreUsuario,
                        style: TextStyle(
                          color: colorScheme.onSurface,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        'OPERADOR ACTIVO',
                        style: TextStyle(
                          color: Colors.greenAccent,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionLabel(BuildContext context, String label) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 4),
      child: Text(
        label,
        style: TextStyle(
          color: cs.onSurfaceVariant.withValues(alpha: 0.5),
          fontSize: 9,
          fontWeight: FontWeight.bold,
          letterSpacing: 2,
        ),
      ),
    );
  }
}
