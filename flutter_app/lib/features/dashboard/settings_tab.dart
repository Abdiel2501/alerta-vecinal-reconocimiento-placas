import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/providers/app_provider.dart';
import '../../core/localization/app_localizations.dart';
import '../../core/services/server_connection_service.dart';
import '../../widgets/glass_container.dart';

class SettingsTab extends StatefulWidget {
  const SettingsTab({super.key});

  @override
  State<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<SettingsTab> {
  bool _mostrarZonaPeligro = false;

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(AppLocalizations.of(context, 'settings_title'), style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: cs.onSurface)),
            const SizedBox(height: 32),
            
            GlassContainer(
              padding: const EdgeInsets.all(8),
              borderRadius: 8,
              child: Material(
                color: Colors.transparent,
                child: ListTile(
                  leading: Icon(isDark ? Icons.dark_mode : Icons.light_mode, color: cs.primary),
                  title: Text(AppLocalizations.of(context, 'theme_title'), style: TextStyle(color: cs.onSurface)),
                  subtitle: Text(AppLocalizations.of(context, 'theme_subtitle'), style: TextStyle(color: cs.onSurfaceVariant)),
                  trailing: Switch(
                    value: isDark,
                    activeColor: cs.primary,
                    onChanged: (val) {
                      provider.setThemeMode(val ? ThemeMode.dark : ThemeMode.light);
                    },
                  ),
                ),
              ),
            ).animate().fadeIn(duration: 400.ms).slideX(begin: 0.1, end: 0),
            const SizedBox(height: 16),
            
            GlassContainer(
              padding: const EdgeInsets.all(8),
              borderRadius: 8,
              child: Material(
                color: Colors.transparent,
                child: Column(
                  children: [
                    ListTile(
                      leading: Icon(Icons.language, color: cs.primary),
                      title: Text(AppLocalizations.of(context, 'lang_title'), style: TextStyle(color: cs.onSurface)),
                      trailing: DropdownButton<String>(
                        value: provider.language,
                        dropdownColor: cs.surfaceContainerHigh,
                        underline: const SizedBox(),
                        items: const [
                          DropdownMenuItem(value: 'es', child: Text('Español')),
                          DropdownMenuItem(value: 'en', child: Text('English')),
                          DropdownMenuItem(value: 'fr', child: Text('Français')),
                          DropdownMenuItem(value: 'de', child: Text('Deutsch')),
                          DropdownMenuItem(value: 'pt', child: Text('Português')),
                        ],
                        onChanged: (val) {
                          if (val != null) provider.setLanguage(val);
                        },
                      ),
                    ),
                    const Divider(color: Colors.white24),
                    ListTile(
                      leading: Icon(Icons.format_size, color: cs.primary),
                      title: Text(AppLocalizations.of(context, 'font_size'), style: TextStyle(color: cs.onSurface)),
                      subtitle: Slider(
                        value: provider.fontScale,
                        min: 0.8,
                        max: 1.4,
                        divisions: 6,
                        activeColor: cs.primary,
                        label: provider.fontScale.toStringAsFixed(1),
                        onChanged: (val) => provider.setFontScale(val),
                      ),
                    ),
                    const Divider(color: Colors.white24),
                    ListTile(
                      leading: Icon(Icons.send, color: cs.primary),
                      title: Text(AppLocalizations.of(context, 'notification_target'), style: TextStyle(color: cs.onSurface)),
                      trailing: DropdownButton<String>(
                        value: provider.notificationTarget,
                        dropdownColor: cs.surfaceContainerHigh,
                        underline: const SizedBox(),
                        items: const [
                          DropdownMenuItem(value: 'telegram', child: Text('Telegram')),
                          DropdownMenuItem(value: 'email', child: Text('Gmail')),
                          DropdownMenuItem(value: 'both', child: Text('Ambos Canales')),
                        ],
                        onChanged: (val) {
                          if (val != null) provider.setNotificationTarget(val);
                        },
                      ),
                    ),
                    
                    // Warning for Telegram missing
                    if ((provider.notificationTarget == 'telegram' || provider.notificationTarget == 'both') &&
                        (provider.usuario?.telegramAlias == null || provider.usuario!.telegramAlias!.trim().isEmpty)) ...[
                      const Divider(color: Colors.white24),
                      ListTile(
                        leading: const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                        title: const Text(
                          '⚠️ Telegram no vinculado',
                          style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        subtitle: const Text(
                          'Presiona aquí para vincular tu Chat ID de Telegram y recibir alertas.',
                          style: TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                        onTap: () => _vincularTelegramDialog(context, provider),
                      ),
                    ],

                    // Warning for Gmail missing
                    if ((provider.notificationTarget == 'email' || provider.notificationTarget == 'both') &&
                        (provider.usuario?.gmailEmail == null || provider.usuario!.gmailEmail!.trim().isEmpty ||
                         provider.usuario?.gmailAppPassword == null || provider.usuario!.gmailAppPassword!.trim().isEmpty)) ...[
                      const Divider(color: Colors.white24),
                      ListTile(
                        leading: const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                        title: const Text(
                          '⚠️ Gmail no configurado',
                          style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        subtitle: const Text(
                          'Presiona aquí para configurar tu remitente y contraseña de aplicación de Gmail.',
                          style: TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                        onTap: () => _vincularGmailDialog(context, provider),
                      ),
                    ],
                  ],
                ),
              ),
            ).animate().fadeIn(duration: 400.ms, delay: 100.ms).slideX(begin: 0.1, end: 0),
            const SizedBox(height: 16),
            
            // --- SECCIÓN: SERVIDOR IA ---
            GlassContainer(
              padding: const EdgeInsets.all(8),
              borderRadius: 8,
              child: Material(
                color: Colors.transparent,
                child: Consumer<ServerConnectionService>(
                  builder: (context, serverSvc, _) {
                    final statusText = switch (serverSvc.state) {
                      ServerConnectionState.connected => 'Conectado (${serverSvc.fps.toStringAsFixed(1)} FPS)',
                      ServerConnectionState.connecting => 'Conectando...',
                      ServerConnectionState.discovering => 'Buscando en red local...',
                      ServerConnectionState.error => 'Error: ${serverSvc.errorMessage}',
                      ServerConnectionState.disconnected => 'Desconectado',
                    };
                    return Column(
                      children: [
                        ListTile(
                          leading: Icon(Icons.dns, color: serverSvc.isConnected ? Colors.greenAccent : cs.primary),
                          title: Text('Servidor IA (Arquitectura Cliente-Servidor)', style: TextStyle(color: cs.onSurface)),
                          subtitle: Text('IP: ${serverSvc.serverIp.isEmpty ? "Automática" : serverSvc.serverIp}:${serverSvc.serverPort} — $statusText', 
                            style: TextStyle(color: cs.onSurfaceVariant)),
                        ),
                        const Divider(color: Colors.white24),
                        ListTile(
                          leading: const Icon(Icons.wifi_find, color: Colors.blueAccent),
                          title: const Text('Cambiar Servidor', style: TextStyle(color: Colors.blueAccent)),
                          subtitle: const Text('Desconectar y buscar o ingresar un nuevo servidor en la red', style: TextStyle(color: Colors.white70)),
                          onTap: () async {
                            await serverSvc.forgetServer();
                            if (context.mounted) {
                              Navigator.pushNamed(context, '/server');
                            }
                          },
                        ),
                      ],
                    );
                  },
                ),
              ),
            ).animate().fadeIn(duration: 400.ms, delay: 110.ms).slideX(begin: 0.1, end: 0),
            const SizedBox(height: 16),
            
            // --- SECCIÓN: GESTIONAR CUENTA ---
            GlassContainer(
              padding: const EdgeInsets.all(8),
              borderRadius: 8,
              child: Material(
                color: Colors.transparent,
                child: Column(
                  children: [
                    ListTile(
                      leading: Icon(Icons.logout, color: cs.primary),
                      title: Text(AppLocalizations.of(context, 'logout'), style: TextStyle(color: cs.onSurface)),
                      subtitle: Text('Cerrar sesión actual y volver a la pantalla de acceso', style: TextStyle(color: cs.onSurfaceVariant)),
                      onTap: () async {
                        await provider.cerrarSesion();
                        if (context.mounted) {
                          Navigator.pushReplacementNamed(context, '/login');
                        }
                      },
                    ),
                    const Divider(color: Colors.white24),
                    ListTile(
                      leading: const Icon(Icons.delete_forever, color: Colors.redAccent),
                      title: const Text('Eliminar Cuenta', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
                      subtitle: const Text('Dar de baja tu cuenta y borrar tus datos del sistema', style: TextStyle(color: Colors.white70)),
                      onTap: () => _iniciarFlujoEliminarCuenta(context, provider),
                    ),
                  ],
                ),
              ),
            ).animate().fadeIn(duration: 400.ms, delay: 120.ms).slideX(begin: 0.1, end: 0),
            
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  void _iniciarFlujoEliminarCuenta(BuildContext context, AppProvider provider) {
    int pasoActual = 1;
    String motivoSeleccionado = 'Ya no necesito el sistema';
    final TextEditingController mensajeController = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext ctx) {
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setDialogState) {
            final theme = Theme.of(context);
            final cs = theme.colorScheme;

            // --- PASO 1: Confirmación Inicial ---
            if (pasoActual == 1) {
              return AlertDialog(
                backgroundColor: cs.surfaceContainerHigh,
                title: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 28),
                    const SizedBox(width: 12),
                    const Text('¿Eliminar tu cuenta?', style: TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
                content: const Text(
                  'Lamentamos mucho que decidas irte. Esta acción es definitiva y borrará todos tus datos encriptados de la base de datos local de forma permanente.\n\n¿Estás seguro de que deseas continuar con la baja?',
                  style: TextStyle(fontSize: 14),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('CANCELAR'),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: cs.error, foregroundColor: Colors.white),
                    onPressed: () {
                      setDialogState(() {
                        pasoActual = 2;
                      });
                    },
                    child: const Text('SÍ, CONTINUAR'),
                  ),
                ],
              );
            }

            // --- PASO 2: Encuesta de Motivos ---
            if (pasoActual == 2) {
              final motivos = [
                'Ya no necesito el sistema',
                'Es muy difícil de usar',
                'Tuve problemas de lag o rendimiento',
                'Demasiados falsos positivos en alertas',
                'Otro motivo'
              ];

              return AlertDialog(
                backgroundColor: cs.surfaceContainerHigh,
                title: const Text('Ayúdanos a mejorar', style: TextStyle(fontWeight: FontWeight.bold)),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Por favor, selecciona el motivo principal de tu baja:',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 12),
                      ...motivos.map((motivo) {
                        return RadioListTile<String>(
                          title: Text(motivo, style: const TextStyle(fontSize: 13, color: Colors.white70)),
                          value: motivo,
                          groupValue: motivoSeleccionado,
                          activeColor: cs.error,
                          contentPadding: EdgeInsets.zero,
                          onChanged: (String? val) {
                            if (val != null) {
                              setDialogState(() {
                                motivoSeleccionado = val;
                              });
                            }
                          },
                        );
                      }),
                      const SizedBox(height: 16),
                      const Text(
                        'Comentarios adicionales (opcional):',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: mensajeController,
                        maxLines: 3,
                        style: const TextStyle(fontSize: 13, color: Colors.white),
                        decoration: InputDecoration(
                          hintText: 'Cuéntanos tu experiencia (opcional)...',
                          hintStyle: TextStyle(color: cs.onSurfaceVariant.withValues(alpha: 0.5)),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () {
                      setDialogState(() {
                        pasoActual = 1;
                      });
                    },
                    child: const Text('ATRÁS'),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: cs.error, foregroundColor: Colors.white),
                    onPressed: () {
                      setDialogState(() {
                        pasoActual = 3;
                      });
                    },
                    child: const Text('CONTINUAR'),
                  ),
                ],
              );
            }

            // --- PASO 3: Confirmación Final ---
            return AlertDialog(
              backgroundColor: cs.surfaceContainerHigh,
              title: Row(
                children: [
                  const Icon(Icons.dangerous, color: Colors.redAccent, size: 30),
                  const SizedBox(width: 12),
                  const Text('Confirmación Final', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.redAccent)),
                ],
              ),
              content: const Text(
                'Esta es la última advertencia. Al confirmar la eliminación, tu cuenta será desactivada y se borrarán todos tus registros.\n\nAdicionalmente, se enviará un mensaje con el motivo de tu baja a los administradores del sistema para fines estadísticos. ¿Confirmas la eliminación?',
                style: TextStyle(fontSize: 14),
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    setDialogState(() {
                      pasoActual = 2;
                    });
                  },
                  child: const Text('ATRÁS'),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () async {
                    Navigator.pop(ctx); // Close dialog
                    
                    await provider.borrarCuentaDefinitivamente(
                      motivo: motivoSeleccionado,
                      mensajeAmano: mensajeController.text,
                    );
                    
                    if (context.mounted) {
                      Navigator.pushReplacementNamed(context, '/login');
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Tu cuenta ha sido eliminada y se ha notificado a los administradores.'),
                          backgroundColor: Colors.redAccent,
                        ),
                      );
                    }
                  },
                  child: const Text('SÍ, ELIMINAR CUENTA'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _vincularTelegramDialog(BuildContext context, AppProvider provider) {
    final controller = TextEditingController(text: provider.usuario?.telegramAlias);
    showDialog(
      context: context,
      builder: (ctx) {
        final cs = Theme.of(context).colorScheme;
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final accentColor = isDark ? Colors.cyanAccent : cs.primary;

        return AlertDialog(
          backgroundColor: cs.surfaceContainerHigh,
          title: Text('Vincular Telegram Chat ID', style: TextStyle(fontWeight: FontWeight.bold, color: cs.onSurface)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Ingresa tu Chat ID de Telegram para recibir alertas directas de vehículos robados.',
                style: TextStyle(fontSize: 13, color: cs.onSurfaceVariant),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: accentColor,
                  side: BorderSide(color: accentColor),
                ),
                icon: const Icon(Icons.open_in_new, size: 16),
                label: const Text('¿No tienes Chat ID? Regístrate aquí', style: TextStyle(fontSize: 12)),
                onPressed: () async {
                  final url = Uri.parse('https://t.me/alerta_vecinaltelegram_bot?start=auth');
                  if (await canLaunchUrl(url)) {
                    await launchUrl(url, mode: LaunchMode.externalApplication);
                  }
                },
              ),
              const SizedBox(height: 16),
              TextField(
                controller: controller,
                style: TextStyle(fontSize: 13, color: cs.onSurface),
                decoration: const InputDecoration(
                  labelText: 'Telegram Chat ID (ej: 123456789)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CANCELAR'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: cs.primary, foregroundColor: cs.onPrimary),
              onPressed: () async {
                if (provider.usuario != null) {
                  final modificado = provider.usuario!.copyWith(
                    telegramAlias: controller.text.trim(),
                  );
                  await provider.actualizarPerfil(modificado);
                }
                if (ctx.mounted) Navigator.pop(ctx);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Chat ID de Telegram vinculado con éxito.')),
                  );
                }
              },
              child: const Text('VINCULAR'),
            ),
          ],
        );
      },
    );
  }

  void _vincularGmailDialog(BuildContext context, AppProvider provider) {
    final emailCtrl = TextEditingController(text: provider.usuario?.gmailEmail);
    final passCtrl = TextEditingController(text: provider.usuario?.gmailAppPassword);

    showDialog(
      context: context,
      builder: (ctx) {
        final cs = Theme.of(context).colorScheme;
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final accentColor = isDark ? Colors.cyanAccent : cs.primary;

        return AlertDialog(
          backgroundColor: cs.surfaceContainerHigh,
          title: Text('Configurar Gmail para Alertas', style: TextStyle(fontWeight: FontWeight.bold, color: cs.onSurface)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Ingresa el correo remitente de Gmail y su contraseña de aplicación de 16 caracteres.',
                style: TextStyle(fontSize: 13, color: cs.onSurfaceVariant),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: accentColor,
                  side: BorderSide(color: accentColor),
                ),
                icon: const Icon(Icons.help_outline, size: 16),
                label: const Text('Obtener contraseña de aplicación', style: TextStyle(fontSize: 12)),
                onPressed: () async {
                  final url = Uri.parse('https://myaccount.google.com/apppasswords');
                  if (await canLaunchUrl(url)) {
                    await launchUrl(url, mode: LaunchMode.externalApplication);
                  }
                },
              ),
              const SizedBox(height: 16),
              TextField(
                controller: emailCtrl,
                style: TextStyle(fontSize: 13, color: cs.onSurface),
                decoration: const InputDecoration(
                  labelText: 'Correo Gmail (ej: mi.correo@gmail.com)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: passCtrl,
                style: TextStyle(fontSize: 13, color: cs.onSurface),
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Contraseña de Aplicación de 16 dígitos',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('CANCELAR'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: cs.primary, foregroundColor: cs.onPrimary),
              onPressed: () async {
                if (provider.usuario != null) {
                  final modificado = provider.usuario!.copyWith(
                    gmailEmail: emailCtrl.text.trim(),
                    gmailAppPassword: passCtrl.text.trim(),
                    gmailHabilitado: emailCtrl.text.trim().isNotEmpty && passCtrl.text.trim().isNotEmpty,
                  );
                  await provider.actualizarPerfil(modificado);
                }
                if (ctx.mounted) Navigator.pop(ctx);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Servidor de alertas Gmail configurado con éxito.')),
                  );
                }
              },
              child: const Text('GUARDAR'),
            ),
          ],
        );
      },
    );
  }
}
