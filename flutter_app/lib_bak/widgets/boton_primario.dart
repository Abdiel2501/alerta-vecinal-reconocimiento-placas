import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class BotonPrimario extends StatefulWidget {
  final String texto_Boton;
  final VoidCallback accion_Boton;
  final bool cargando_Estado;
  final double? ancho_Boton;

  const BotonPrimario({
    super.key,
    required this.texto_Boton,
    required this.accion_Boton,
    this.cargando_Estado = false,
    this.ancho_Boton,
  });

  @override
  State<BotonPrimario> createState() => _BotonPrimarioState();
}

class _BotonPrimarioState extends State<BotonPrimario> {
  bool hover_Activo = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => hover_Activo = true),
      onExit: (_) => setState(() => hover_Activo = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: widget.ancho_Boton ?? double.infinity,
        height: 52,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          gradient: LinearGradient(
            colors: hover_Activo
                ? [
                    AppTheme.color_Acento,
                    AppTheme.color_AcentoGradiente,
                  ]
                : [
                    AppTheme.color_AcentoSecundario,
                    AppTheme.color_Acento.withOpacity(0.8),
                  ],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.color_Acento
                  .withOpacity(hover_Activo ? 0.45 : 0.25),
              blurRadius: hover_Activo ? 24 : 12,
              spreadRadius: 0,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: widget.cargando_Estado ? null : widget.accion_Boton,
            child: Center(
              child: widget.cargando_Estado
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        color: Colors.white,
                        strokeWidth: 2,
                      ),
                    )
                  : Text(
                      widget.texto_Boton,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
