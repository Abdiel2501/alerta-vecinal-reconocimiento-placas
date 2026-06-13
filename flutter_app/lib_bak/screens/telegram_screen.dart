import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../widgets/boton_primario.dart';
import 'dashboard_screen.dart';

class TelegramScreen extends StatefulWidget {
  final String nombre_Ingresado;

  const TelegramScreen({super.key, required this.nombre_Ingresado});

  @override
  State<TelegramScreen> createState() => _TelegramScreenState();
}

class _TelegramScreenState extends State<TelegramScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController controlador_Telegram = TextEditingController();
  final GlobalKey<FormState> clave_Formulario = GlobalKey<FormState>();

  bool cargando_Vinculo = false;
  late AnimationController animacion_Controlador;
  late Animation<double> animacion_Opacidad;
  late Animation<Offset> animacion_Posicion;

  @override
  void initState() {
    super.initState();
    animacion_Controlador = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    animacion_Opacidad = CurvedAnimation(
      parent: animacion_Controlador,
      curve: Curves.easeOut,
    );
    animacion_Posicion = Tween<Offset>(
      begin: const Offset(0.05, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: animacion_Controlador,
      curve: Curves.easeOut,
    ));
    animacion_Controlador.forward();
  }

  @override
  void dispose() {
    animacion_Controlador.dispose();
    controlador_Telegram.dispose();
    super.dispose();
  }

  String _limpiar_Alias(String alias_Crudo) {
    return alias_Crudo.replaceAll('@', '').trim();
  }

  void _vincular_Telegram() async {
    if (!clave_Formulario.currentState!.validate()) return;
    setState(() => cargando_Vinculo = true);
    await Future.delayed(const Duration(milliseconds: 700));
    if (!mounted) return;
    setState(() => cargando_Vinculo = false);
    String telegram_Alias = _limpiar_Alias(controlador_Telegram.text);
    Navigator.push(
      context,
      PageRouteBuilder(
        pageBuilder: (_, anim_A, anim_B) => DashboardScreen(
          nombre_Usuario: widget.nombre_Ingresado,
          telegram_Alias: telegram_Alias,
        ),
        transitionsBuilder: (_, anim_A, anim_B, child_Transition) {
          return FadeTransition(opacity: anim_A, child: child_Transition);
        },
        transitionDuration: const Duration(milliseconds: 400),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          _construir_FondoAnimado(),
          Center(
            child: SingleChildScrollView(
              child: FadeTransition(
                opacity: animacion_Opacidad,
                child: SlideTransition(
                  position: animacion_Posicion,
                  child: GlassContainer(
                    ancho_Contenedor: 480,
                    child_Widget: Form(
                      key: clave_Formulario,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _construir_Progreso(),
                          const SizedBox(height: 28),
                          _construir_Encabezado(),
                          const SizedBox(height: 32),
                          _construir_BannerInfo(),
                          const SizedBox(height: 24),
                          _construir_CampoTelegram(),
                          const SizedBox(height: 28),
                          BotonPrimario(
                            texto_Boton: 'Vincular y Continuar',
                            accion_Boton: _vincular_Telegram,
                            cargando_Estado: cargando_Vinculo,
                          ),
                          const SizedBox(height: 16),
                          _construir_BotonVolver(),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _construir_Progreso() {
    return Row(
      children: List.generate(3, (indice_Item) {
        bool activo_Item = indice_Item <= 1;
        bool actual_Item = indice_Item == 1;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.only(right: 6),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: 3,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                color: actual_Item
                    ? AppTheme.color_Acento
                    : activo_Item
                        ? AppTheme.color_Acento.withOpacity(0.4)
                        : AppTheme.color_Borde,
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _construir_Encabezado() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: const Color(0xFF00D4FF).withOpacity(0.12),
            border: Border.all(
                color: const Color(0xFF00D4FF).withOpacity(0.3), width: 1),
          ),
          child: const Icon(
            Icons.send_rounded,
            color: AppTheme.color_Acento,
            size: 22,
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'Conectar Telegram',
          style: GoogleFonts.outfit(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            color: AppTheme.color_Texto,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Ingresa tu usuario de Telegram para recibir alertas automaticas de vehiculos robados.',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppTheme.color_TextoTenue,
            height: 1.6,
          ),
        ),
      ],
    );
  }

  Widget _construir_BannerInfo() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: AppTheme.color_Acento.withOpacity(0.06),
        border: Border.all(
            color: AppTheme.color_Acento.withOpacity(0.2), width: 1),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline_rounded,
            color: AppTheme.color_Acento,
            size: 18,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Solo necesitas tu usuario de Telegram, no tu numero de telefono. Puedes encontrarlo en Configuracion dentro de la aplicacion.',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: AppTheme.color_Acento.withOpacity(0.9),
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _construir_CampoTelegram() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Usuario de Telegram',
          style: GoogleFonts.inter(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppTheme.color_TextoTenue,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          controller: controlador_Telegram,
          style: GoogleFonts.inter(
              color: AppTheme.color_Texto, fontSize: 14),
          validator: (valor_Campo) {
            if (valor_Campo == null || valor_Campo.trim().isEmpty) {
              return 'El usuario de Telegram no puede estar vacio';
            }
            return null;
          },
          decoration: InputDecoration(
            hintText: '@tu_usuario',
            prefixIcon: const Icon(
              Icons.alternate_email_rounded,
              color: AppTheme.color_TextoTenue,
              size: 18,
            ),
          ),
        ),
      ],
    );
  }

  Widget _construir_BotonVolver() {
    return Center(
      child: TextButton.icon(
        onPressed: () => Navigator.pop(context),
        icon: const Icon(
          Icons.arrow_back_ios_rounded,
          size: 14,
          color: AppTheme.color_TextoTenue,
        ),
        label: Text(
          'Volver al paso anterior',
          style: GoogleFonts.inter(
            fontSize: 13,
            color: AppTheme.color_TextoTenue,
          ),
        ),
      ),
    );
  }

  Widget _construir_FondoAnimado() {
    return Stack(
      children: [
        Positioned(
          top: -80,
          right: -80,
          child: _construir_BlobbeFondo(const Color(0xFF00D4FF), 280),
        ),
        Positioned(
          bottom: -100,
          left: -60,
          child: _construir_BlobbeFondo(const Color(0xFF1F6FEB), 320),
        ),
      ],
    );
  }

  Widget _construir_BlobbeFondo(Color color_Blob, double tamano_Blob) {
    return Container(
      width: tamano_Blob,
      height: tamano_Blob,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color_Blob.withOpacity(0.08),
        boxShadow: [
          BoxShadow(
            color: color_Blob.withOpacity(0.2),
            blurRadius: 100,
            spreadRadius: 30,
          ),
        ],
      ),
    );
  }
}
