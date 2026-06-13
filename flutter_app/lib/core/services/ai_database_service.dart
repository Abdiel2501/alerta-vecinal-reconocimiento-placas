import 'dart:io';
import 'package:path/path.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class AiAlert {
  final int id;
  final String placaBd;
  final String placaDetectada;
  final double similitud;
  final String fechaAlerta;
  final String rutaFotoVehiculo;
  final String rutaFotoPlaca;

  AiAlert({
    required this.id,
    required this.placaBd,
    required this.placaDetectada,
    required this.similitud,
    required this.fechaAlerta,
    required this.rutaFotoVehiculo,
    required this.rutaFotoPlaca,
  });

  factory AiAlert.fromMap(Map<String, dynamic> map) {
    return AiAlert(
      id: map['id'] as int,
      placaBd: map['placa'] as String? ?? '',
      placaDetectada: map['placa_detectada'] as String? ?? '',
      similitud: (map['similitud'] as num?)?.toDouble() ?? 0.0,
      fechaAlerta: map['fecha_alerta'] as String? ?? '',
      rutaFotoVehiculo: map['ruta_foto_vehiculo'] as String? ?? '',
      rutaFotoPlaca: map['ruta_foto_placa'] as String? ?? '',
    );
  }
}

class AiDatabaseService {
  static Database? _db;

  static String _getDbPath() {
    final appData = Platform.environment['APPDATA'] ?? '';
    return join(appData, 'AlertaVecinal', 'System', 'secure_placas.db');
  }

  static Future<void> initialize() async {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  }

  static Future<Database?> get database async {
    // Verificar si el archivo existe antes de intentar abrirlo
    final path = _getDbPath();
    if (!File(path).existsSync()) {
      _db = null; // Resetear si se borró
      return null; // La IA aún no ha creado la BD
    }
    if (_db != null) return _db!;
    _db = await _initDB(path);
    return _db!;
  }

  static Future<Database> _initDB(String path) async {
    return await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        readOnly: true,
      ),
    );
  }

  static Future<List<AiAlert>> getRecentAlerts({int limit = 10}) async {
    try {
      final db = await database;
      if (db == null) return []; // BD no lista todavía, sin error
      final List<Map<String, dynamic>> maps = await db.query(
        'historial_alertas',
        orderBy: 'fecha_alerta DESC',
        limit: limit,
      );
      return maps.map((e) => AiAlert.fromMap(e)).toList();
    } catch (e) {
      // Si hay error de lectura, resetear conexión para el próximo intento
      _db = null;
      return [];
    }
  }

  static Future<bool> clearAlertsHistory() async {
    try {
      final path = _getDbPath();
      if (!File(path).existsSync()) return false;
      
      // Cerrar conexión de solo lectura si está activa
      if (_db != null) {
        await _db!.close();
        _db = null;
      }
      
      // Abrir temporalmente en modo lectura-escritura para borrar
      final rwDb = await databaseFactory.openDatabase(path);
      await rwDb.delete('historial_alertas');
      await rwDb.close();
      return true;
    } catch (e) {
      return false;
    }
  }
}
