import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class GlassContainer extends StatelessWidget {
  final Widget child_Widget;
  final double? ancho_Contenedor;
  final double? alto_Contenedor;
  final EdgeInsets? padding_Interno;
  final double radio_Borde;

  const GlassContainer({
    super.key,
    required this.child_Widget,
    this.ancho_Contenedor,
    this.alto_Contenedor,
    this.padding_Interno,
    this.radio_Borde = 20,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radio_Borde),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          width: ancho_Contenedor,
          height: alto_Contenedor,
          padding: padding_Interno ?? const EdgeInsets.all(36),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.04),
            borderRadius: BorderRadius.circular(radio_Borde),
            border: Border.all(
              color: Colors.white.withOpacity(0.08),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.5),
                blurRadius: 40,
                spreadRadius: 0,
                offset: const Offset(0, 16),
              ),
              BoxShadow(
                color: AppTheme.color_Acento.withOpacity(0.04),
                blurRadius: 60,
                spreadRadius: -5,
              ),
            ],
          ),
          child: child_Widget,
        ),
      ),
    );
  }
}
