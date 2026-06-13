class AlertModel {
  final String id;
  final String placa;
  final String tipo; // 'robado', 'sospechoso', 'autorizado'
  final String color;
  final String marca;
  final double confianza;
  final DateTime timestamp;
  final String ubicacion;
  final String? imagenUrl;

  AlertModel({
    required this.id,
    required this.placa,
    required this.tipo,
    required this.color,
    required this.marca,
    required this.confianza,
    required this.timestamp,
    required this.ubicacion,
    this.imagenUrl,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'placa': placa,
      'tipo': tipo,
      'color': color,
      'marca': marca,
      'confianza': confianza,
      'timestamp': timestamp.toIso8601String(),
      'ubicacion': ubicacion,
      'imagenUrl': imagenUrl,
    };
  }

  factory AlertModel.fromMap(Map<String, dynamic> map) {
    return AlertModel(
      id: map['id'],
      placa: map['placa'],
      tipo: map['tipo'],
      color: map['color'],
      marca: map['marca'],
      confianza: map['confianza'],
      timestamp: DateTime.parse(map['timestamp']),
      ubicacion: map['ubicacion'],
      imagenUrl: map['imagenUrl'],
    );
  }
}

enum NotificacionTipo { alerta, sistema, telegram }

class NotificationModel {
  final String id;
  final String titulo;
  final String cuerpo;
  final DateTime timestamp;
  final NotificacionTipo tipo;
  bool leida;

  NotificationModel({
    required this.id,
    required this.titulo,
    required this.cuerpo,
    required this.timestamp,
    required this.tipo,
    this.leida = false,
  });
}
