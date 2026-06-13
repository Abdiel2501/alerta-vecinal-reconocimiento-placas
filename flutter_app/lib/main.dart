import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';
import 'package:window_manager/window_manager.dart';
import 'core/providers/app_provider.dart';
import 'core/services/database_service.dart';
import 'core/services/hardware_service.dart';
import 'core/services/recording_service.dart';
import 'core/services/camera_manager_service.dart';
import 'core/services/server_connection_service.dart';
import 'features/splash/splash_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/register_screen.dart';
import 'features/auth/verify_pin_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/server/server_connect_screen.dart';
import 'theme/app_theme.dart';

void main() async {
  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      FlutterError.onError = (details) {
        FlutterError.presentError(details);
        // ignore: avoid_print
        print('[FLUTTER ERROR] ${details.exceptionAsString()}\n${details.stack}');
      };

      await initializeDateFormatting('es_MX', null);
      await DatabaseService.initialize();

      if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
        await windowManager.ensureInitialized();
        const options = WindowOptions(
          size: Size(1440, 860),
          minimumSize: Size(1100, 650),
          center: true,
          title: 'Alerta Vecinal — ANPR Tactical Client',
          backgroundColor: Colors.transparent,
          skipTaskbar: false,
          titleBarStyle: TitleBarStyle.normal,
        );
        await windowManager.waitUntilReadyToShow(options, () async {
          await windowManager.show();
          await windowManager.focus();
        });
      }

      runApp(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => AppProvider()),
            ChangeNotifierProvider(create: (_) => HardwareService()..initialize()),
            ChangeNotifierProvider(create: (_) => RecordingService()),
            ChangeNotifierProvider(create: (_) => CameraManagerService()),
            // Servicio de conexión al Servidor IA (WebSocket + auto-descubrimiento)
            ChangeNotifierProvider(create: (_) => ServerConnectionService()),
          ],
          child: const AlertaVecinalApp(),
        ),
      );
    },
    (error, stack) {
      // ignore: avoid_print
      print('[FATAL UNHANDLED] $error\n$stack');
    },
  );
}

class AlertaVecinalApp extends StatelessWidget {
  const AlertaVecinalApp({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    return MaterialApp(
      title: 'Alerta Vecinal',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: provider.themeMode,
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(provider.fontScale),
          ),
          child: child!,
        );
      },
      initialRoute: '/',
      routes: {
        '/': (_) => const SplashScreen(),
        '/login': (_) => const LoginScreen(),
        '/register': (_) => const RegisterScreen(),
        '/verify_pin': (_) => const VerifyPinScreen(),
        '/server': (_) => const ServerConnectScreen(),
        '/dashboard': (_) => const DashboardScreen(),
      },
    );
  }
}
