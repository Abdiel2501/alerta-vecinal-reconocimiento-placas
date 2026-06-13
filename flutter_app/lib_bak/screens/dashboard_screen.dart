import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_container.dart';

class DashboardScreen extends StatefulWidget {
  final String nombre_Usuario;
  final String telegram_Alias;

  const DashboardScreen({
    super.key,
    required this.nombre_Usuario,
    required this.telegram_Alias,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with SingleTickerProviderStateMixin {
  static const String nombre_Bot = 'alerta_vecinaltelegram_bot';

  bool hover_BotonTelegram = false;
  late AnimationController animacion_Controlador;
  late Animation<double> animacion_Opacidad;

  @override
  void initState() {
    super.initState();
    animacion_Controlador = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    animacion_Opacidad = CurvedAnimation(
      parent: animacion_Controlador,
      curve: Curves.easeOut,
    );
    animacion_Controlador.forward();
  }

  @override
  void dispose() {
    animacion_Controlador.dispose();
    super.dispose();
  }

  Future<void> _abrir_Bot() async {
    final Uri uri_Telegram = Uri.parse(
        'https://t.me/$nombre_Bot?start=auth_${widget.telegram_Alias}');
    if (await canLaunchUrl(uri_Telegram)) {
      await launchUrl(uri_Telegram, mode: LaunchMode.externalApplication);
    }
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
                child: Column(
                  children: [
                    _construir_TarjetaBienvenida(),
                    const SizedBox(height: 24),
                    _construir_TarjetaPasos(),
                    const SizedBox(height: 24),
                    _construir_BotonBot(),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _construir_TarjetaBienvenida() {
    return GlassContainer(
      ancho_Contenedor: 560,
      child_Widget: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _construir_Progreso(),
            ],
          ),
          const SizedBox(height: 28),
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1F6FEB), Color(0xFF00D4FF)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: const Icon(Icons.check_rounded,
                    color: Colors.white, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Configuracion completada',
                      style: GoogleFonts.outfit(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.color_Texto,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Bienvenido, ${widget.nombre_Usuario}',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: AppTheme.color_Acento,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: Colors.white.withOpacity(0.03),
              border: Border.all(
                  color: Colors.white.withOpacity(0.06), width: 1),
            ),
            child: Row(
              children: [
                const Icon(Icons.alternate_email_rounded,
                    size: 16, color: AppTheme.color_TextoTenue),
                const SizedBox(width: 10),
                Text(
                  'Telegram vinculado: ',
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppTheme.color_TextoTenue,
                  ),
                ),
                Text(
                  '@${widget.telegram_Alias}',
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppTheme.color_Acento,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _construir_TarjetaPasos() {
    final List<Map<String, dynamic>> pasos_Lista = [
      {
        'numero_Paso': '01',
        'titulo_Paso': 'Abre tu bot personal',
        'descripcion_Paso':
            'Presiona el boton de abajo para acceder directamente al bot configurado con tu cuenta.',
        'icono_Paso': Icons.open_in_new_rounded,
      },
      {
        'numero_Paso': '02',
        'titulo_Paso': 'Presiona Iniciar en Telegram',
        'descripcion_Paso':
            'Dentro del chat del bot, toca el boton Iniciar o escribe /start para activar la recepcion de alertas.',
        'icono_Paso': Icons.touch_app_outlined,
      },
      {
        'numero_Paso': '03',
        'titulo_Paso': 'Recibe alertas automaticamente',
        'descripcion_Paso':
            'Cuando el sistema detecte un vehiculo con reporte de robo, recibiras la fotografia y los detalles al instante.',
        'icono_Paso': Icons.notifications_active_outlined,
      },
    ];

    return GlassContainer(
      ancho_Contenedor: 560,
      child_Widget: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Que hacer a continuacion',
            style: GoogleFonts.outfit(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppTheme.color_Texto,
            ),
          ),
          const SizedBox(height: 24),
          ...pasos_Lista.asMap().entries.map((entrada_Mapa) {
            int indice_Item = entrada_Mapa.key;
            Map<String, dynamic> paso_Item = entrada_Mapa.value;
            bool ultimo_Item = indice_Item == pasos_Lista.length - 1;
            return _construir_PasoItem(paso_Item, ultimo_Item);
          }),
        ],
      ),
    );
  }

  Widget _construir_PasoItem(
      Map<String, dynamic> paso_Data, bool ultimo_Paso) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.color_Acento.withOpacity(0.1),
                border: Border.all(
                    color: AppTheme.color_Acento.withOpacity(0.3), width: 1),
              ),
              child: Center(
                child: Text(
                  paso_Data['numero_Paso'],
                  style: GoogleFonts.outfit(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.color_Acento,
                  ),
                ),
              ),
            ),
            if (!ultimo_Paso)
              Container(
                width: 1,
                height: 52,
                margin: const EdgeInsets.symmetric(vertical: 6),
                color: AppTheme.color_Borde,
              ),
          ],
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  paso_Data['titulo_Paso'],
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.color_Texto,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  paso_Data['descripcion_Paso'],
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppTheme.color_TextoTenue,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _construir_BotonBot() {
    return MouseRegion(
      onEnter: (_) => setState(() => hover_BotonTelegram = true),
      onExit: (_) => setState(() => hover_BotonTelegram = false),
      child: GestureDetector(
        onTap: _abrir_Bot,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          width: 560,
          height: 64,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: LinearGradient(
              colors: hover_BotonTelegram
                  ? [
                      const Color(0xFF00D4FF),
                      const Color(0xFF7C3AED),
                    ]
                  : [
                      const Color(0xFF0099CC),
                      const Color(0xFF5B21B6),
                    ],
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF00D4FF)
                    .withOpacity(hover_BotonTelegram ? 0.5 : 0.25),
                blurRadius: hover_BotonTelegram ? 32 : 16,
                spreadRadius: 0,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.send_rounded, color: Colors.white, size: 20),
              const SizedBox(width: 12),
              Text(
                'Abrir mi bot en Telegram',
                style: GoogleFonts.outfit(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.3,
                ),
              ),
              const SizedBox(width: 10),
              AnimatedSlide(
                duration: const Duration(milliseconds: 200),
                offset: hover_BotonTelegram
                    ? const Offset(0.2, 0)
                    : Offset.zero,
                child: const Icon(Icons.arrow_forward_rounded,
                    color: Colors.white70, size: 18),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _construir_Progreso() {
    return Expanded(
      child: Row(
        children: List.generate(3, (indice_Item) {
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Container(
                height: 3,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: AppTheme.color_Acento,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _construir_FondoAnimado() {
    return Stack(
      children: [
        Positioned(
          top: -100,
          left: -80,
          child: _construir_BlobbeFondo(const Color(0xFF7C3AED), 300),
        ),
        Positioned(
          bottom: -80,
          right: -60,
          child: _construir_BlobbeFondo(const Color(0xFF00D4FF), 260),
        ),
        Positioned(
          top: 200,
          right: 100,
          child: _construir_BlobbeFondo(const Color(0xFF1F6FEB), 200),
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
        color: color_Blob.withOpacity(0.07),
        boxShadow: [
          BoxShadow(
            color: color_Blob.withOpacity(0.18),
            blurRadius: 100,
            spreadRadius: 20,
          ),
        ],
      ),
    );
  }
}
