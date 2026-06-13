import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';
import '../widgets/boton_primario.dart';
import 'telegram_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController controlador_Nombre = TextEditingController();
  final TextEditingController controlador_Contrasena = TextEditingController();
  final GlobalKey<FormState> clave_Formulario = GlobalKey<FormState>();

  bool visible_Contrasena = false;
  bool cargando_Sesion = false;
  late AnimationController animacion_Controlador;
  late Animation<double> animacion_Opacidad;
  late Animation<Offset> animacion_Posicion;

  @override
  void initState() {
    super.initState();
    animacion_Controlador = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    animacion_Opacidad = CurvedAnimation(
      parent: animacion_Controlador,
      curve: Curves.easeOut,
    );
    animacion_Posicion = Tween<Offset>(
      begin: const Offset(0, 0.08),
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
    controlador_Nombre.dispose();
    controlador_Contrasena.dispose();
    super.dispose();
  }

  Widget _construir_CampoTexto({
    required TextEditingController controlador_Campo,
    required String etiqueta_Campo,
    required String pista_Campo,
    required IconData icono_Campo,
    bool oscurecer_Texto = false,
    Widget? sufijo_Widget,
    String? Function(String?)? validador_Campo,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          etiqueta_Campo,
          style: GoogleFonts.inter(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppTheme.color_TextoTenue,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          controller: controlador_Campo,
          obscureText: oscurecer_Texto,
          validator: validador_Campo,
          style: GoogleFonts.inter(
            color: AppTheme.color_Texto,
            fontSize: 14,
          ),
          decoration: InputDecoration(
            hintText: pista_Campo,
            prefixIcon: Icon(
              icono_Campo,
              color: AppTheme.color_TextoTenue,
              size: 18,
            ),
            suffixIcon: sufijo_Widget,
          ),
        ),
      ],
    );
  }

  void _continuar_Registro() async {
    if (!clave_Formulario.currentState!.validate()) return;
    setState(() => cargando_Sesion = true);
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    setState(() => cargando_Sesion = false);
    String nombre_Usuario = controlador_Nombre.text.trim();
    Navigator.push(
      context,
      PageRouteBuilder(
        pageBuilder: (_, anim_A, anim_B) =>
            TelegramScreen(nombre_Ingresado: nombre_Usuario),
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
                    ancho_Contenedor: 460,
                    child_Widget: Form(
                      key: clave_Formulario,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _construir_Encabezado(),
                          const SizedBox(height: 36),
                          _construir_CampoTexto(
                            controlador_Campo: controlador_Nombre,
                            etiqueta_Campo: 'Nombre completo',
                            pista_Campo: 'Tu nombre de usuario',
                            icono_Campo: Icons.person_outline_rounded,
                            validador_Campo: (valor_Campo) {
                              if (valor_Campo == null || valor_Campo.isEmpty) {
                                return 'El nombre no puede estar vacio';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 20),
                          _construir_CampoTexto(
                            controlador_Campo: controlador_Contrasena,
                            etiqueta_Campo: 'Contrasena',
                            pista_Campo: 'Minimo 6 caracteres',
                            icono_Campo: Icons.lock_outline_rounded,
                            oscurecer_Texto: !visible_Contrasena,
                            sufijo_Widget: IconButton(
                              icon: Icon(
                                visible_Contrasena
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                                color: AppTheme.color_TextoTenue,
                                size: 18,
                              ),
                              onPressed: () => setState(
                                  () => visible_Contrasena = !visible_Contrasena),
                            ),
                            validador_Campo: (valor_Campo) {
                              if (valor_Campo == null || valor_Campo.length < 6) {
                                return 'La contrasena debe tener al menos 6 caracteres';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 32),
                          BotonPrimario(
                            texto_Boton: 'Continuar',
                            accion_Boton: _continuar_Registro,
                            cargando_Estado: cargando_Sesion,
                          ),
                          const SizedBox(height: 20),
                          _construir_PiePagina(),
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

  Widget _construir_FondoAnimado() {
    return Stack(
      children: [
        Positioned(
          top: -120,
          left: -120,
          child: _construir_BlobbeFondo(
              const Color(0xFF1F6FEB), 350),
        ),
        Positioned(
          bottom: -150,
          right: -100,
          child: _construir_BlobbeFondo(
              const Color(0xFF7C3AED), 400),
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
        color: color_Blob.withOpacity(0.12),
        boxShadow: [
          BoxShadow(
            color: color_Blob.withOpacity(0.3),
            blurRadius: 120,
            spreadRadius: 40,
          ),
        ],
      ),
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
            gradient: const LinearGradient(
              colors: [Color(0xFF1F6FEB), Color(0xFF00D4FF)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: const Icon(
            Icons.shield_outlined,
            color: Colors.white,
            size: 26,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Configuracion del Sistema',
          style: GoogleFonts.outfit(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            color: AppTheme.color_Texto,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Crea tu cuenta para gestionar las alertas de vigilancia',
          style: GoogleFonts.inter(
            fontSize: 14,
            color: AppTheme.color_TextoTenue,
            height: 1.5,
          ),
        ),
      ],
    );
  }

  Widget _construir_PiePagina() {
    return Center(
      child: Text(
        'Sistema de Vigilancia Inteligente v1.0',
        style: GoogleFonts.inter(
          fontSize: 12,
          color: AppTheme.color_TextoTenue.withOpacity(0.6),
        ),
      ),
    );
  }
}
