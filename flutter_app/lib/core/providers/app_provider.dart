import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../models/user_model.dart';
import '../models/alert_model.dart';
import '../services/auth_service.dart';
import '../services/database_service.dart';
import '../services/gmail_service.dart';

class AppProvider extends ChangeNotifier {
  UserModel? _usuario;
  List<AlertModel> _alertas = [];
  List<NotificationModel> _notificaciones = [];
  bool _cargando = false;
  int _tabActual = 0;
  ThemeMode _themeMode = ThemeMode.system;
  String _language = 'es';
  double _fontScale = 1.0;
  String _notificationTarget = 'telegram';

  AppProvider() {
    _cargarTemaGuardado();
  }

  // ─── Getters ─────────────────────────────────────────────────────────
  UserModel? get usuario => _usuario;
  List<AlertModel> get alertas => _alertas;
  List<NotificationModel> get notificaciones => _notificaciones;
  bool get cargando => _cargando;
  int get tabActual => _tabActual;
  ThemeMode get themeMode => _themeMode;
  String get language => _language;
  double get fontScale => _fontScale;
  String get notificationTarget => _notificationTarget;
  int get notificacionesSinLeer => _notificaciones.where((n) => !n.leida).length;

  // ─── Preferencias de Tema ──────────────────────────────────────────
  Future<void> _cargarTemaGuardado() async {
    final prefs = await SharedPreferences.getInstance();
    final index = prefs.getInt('themeMode');
    if (index != null && index >= 0 && index < ThemeMode.values.length) {
      _themeMode = ThemeMode.values[index];
    }
    final target = prefs.getString('notificationTarget');
    if (target != null) {
      _notificationTarget = target;
    }
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('themeMode', mode.index);
  }

  void setLanguage(String langCode) {
    if (_language != langCode) {
      _language = langCode;
      notifyListeners();
    }
  }

  void setFontScale(double scale) {
    if (_fontScale != scale) {
      _fontScale = scale;
      notifyListeners();
    }
  }

  Future<void> setNotificationTarget(String target) async {
    if (_notificationTarget != target) {
      _notificationTarget = target;
      notifyListeners();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('notificationTarget', target);
    }
  }

  // ─── Control de Estado ───────────────────────────────────────────────
  void setCargando(bool val) {
    _cargando = val;
    notifyListeners();
  }

  void setTabActual(int index) {
    _tabActual = index;
    notifyListeners();
  }

  // ─── Autenticación ───────────────────────────────────────────────────
  Future<AuthResult> login(String email, String password) async {
    setCargando(true);
    final result = await AuthService.login(email, password);
    if (result.exito && result.usuario != null) {
      _usuario = result.usuario;
    }
    setCargando(false);
    return result;
  }

  Future<AuthResult> registrar(String nombre, String email, String password) async {
    setCargando(true);
    final result = await AuthService.register(nombre, email, password);
    if (result.exito && result.usuario != null) {
      _usuario = result.usuario;
    }
    setCargando(false);
    return result;
  }

  Future<AuthResult> iniciarSesionGoogle() async {
    setCargando(true);
    final result = await AuthService.signInWithGoogle();
    if (result.exito && result.usuario != null) {
      _usuario = result.usuario;
    }
    setCargando(false);
    return result;
  }

  Future<void> cerrarSesion() async {
    await AuthService.logout();
    _usuario = null;
    _alertas.clear();
    _notificaciones.clear();
    _tabActual = 0;
    notifyListeners();
  }

  Future<void> borrarCuentaDefinitivamente({required String motivo, String? mensajeAmano}) async {
    if (_usuario == null) return;
    setCargando(true);
    
    final nombre = _usuario!.nombre;
    final email = _usuario!.email;
    
    // --- NOTIFICACIÓN ADMINISTRATIVA DE BAJA ---
    print('\n🚨 [ADMIN ALERT] SOLICITUD DE BAJA DE OPERADOR');
    print('👤 Operador: $nombre ($email)');
    print('📋 Motivo de salida: $motivo');
    if (mensajeAmano != null && mensajeAmano.trim().isNotEmpty) {
      print('📝 Mensaje adicional: $mensajeAmano');
    }
    print('─────────────────────────────────────────\n');

    await DatabaseService.deleteUser(_usuario!.email);
    await cerrarSesion();
    setCargando(false);
  }

  Future<bool> verificarSesionActiva() async {
    _usuario = await AuthService.checkActiveSession();
    notifyListeners();
    return _usuario != null;
  }

  Future<void> actualizarPerfil(UserModel userModificado) async {
    await DatabaseService.updateUser(userModificado);
    _usuario = userModificado;
    notifyListeners();
  }

  // ─── Alertas ─────────────────────────────────────────────────────────
  void registrarAlerta({
    required String placa,
    required String tipo,
    required String color,
    required String marca,
    required double confianza,
    required String ubicacion,
  }) {
    final nuevaAlerta = AlertModel(
      id: const Uuid().v4(),
      placa: placa,
      tipo: tipo,
      color: color,
      marca: marca,
      confianza: confianza,
      timestamp: DateTime.now(),
      ubicacion: ubicacion,
    );

    _alertas.insert(0, nuevaAlerta);
    
    if (tipo == 'robado') {
      _agregarNotificacion(
        titulo: '¡ALERTA CRÍTICA!',
        cuerpo: 'Vehículo robado detectado: $placa ($marca $color) en $ubicacion',
        tipo: NotificacionTipo.alerta,
      );
    }
    
    notifyListeners();
  }

  // ─── Notificaciones ──────────────────────────────────────────────────
  void _agregarNotificacion({
    required String titulo,
    required String cuerpo,
    required NotificacionTipo tipo,
  }) {
    _notificaciones.insert(
      0,
      NotificationModel(
        id: const Uuid().v4(),
        titulo: titulo,
        cuerpo: cuerpo,
        timestamp: DateTime.now(),
        tipo: tipo,
      ),
    );
    notifyListeners();
  }

  void marcarNotificacionesLeidas() {
    for (var n in _notificaciones) {
      n.leida = true;
    }
    notifyListeners();
  }

  void agregarNotificacionSistema(String titulo, String cuerpo) {
    _agregarNotificacion(titulo: titulo, cuerpo: cuerpo, tipo: NotificacionTipo.sistema);
  }
}
