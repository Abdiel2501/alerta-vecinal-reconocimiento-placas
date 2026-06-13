import 'package:mailer/mailer.dart';
import 'package:mailer/smtp_server.dart';
import '../models/user_model.dart';

class GmailService {
  // ─── Correo de recuperación de contraseña ──────────────────────────────
  static Future<bool> sendPasswordRecoveryEmail(UserModel user, String pin) async {
    if (user.gmailEmail == null || user.gmailAppPassword == null) {
      print('Simulando envío de correo de recuperación a ${user.email}. PIN: $pin');
      return true;
    }
    return _send(
      smtpEmail: user.gmailEmail!,
      smtpPassword: user.gmailAppPassword!,
      toEmail: user.email,
      subject: 'Recuperación de Contraseña — Alerta Vecinal',
      htmlBody: _templateBase(
        title: 'Recuperación de Acceso',
        accentColor: '#FF3D57',
        icon: '🔑',
        bodyHtml: '''
          <p>Hola <strong>${user.nombre}</strong>,</p>
          <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>
          <div style="background:#1A2035;border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
            <p style="color:#aaa;margin:0 0 8px 0;font-size:13px;">TU CÓDIGO DE SEGURIDAD</p>
            <h1 style="color:#fff;font-size:38px;letter-spacing:12px;margin:0;font-family:monospace;">$pin</h1>
            <p style="color:#888;font-size:11px;margin:12px 0 0 0;">Válido por 15 minutos</p>
          </div>
          <p style="color:#888;font-size:12px;">Si no fuiste tú, ignora este mensaje. Tu cuenta está segura.</p>
        ''',
      ),
    );
  }

  // ─── Correo de bienvenida al registrarse ──────────────────────────────
  static Future<bool> sendWelcomeEmail(UserModel user) async {
    if (user.gmailEmail == null || user.gmailAppPassword == null) {
      print('Sin SMTP configurado — simulando bienvenida a ${user.email}');
      return true;
    }
    return _send(
      smtpEmail: user.gmailEmail!,
      smtpPassword: user.gmailAppPassword!,
      toEmail: user.email,
      subject: '¡Bienvenido a Alerta Vecinal! 🎉',
      htmlBody: _templateBase(
        title: '¡Cuenta activada!',
        accentColor: '#00D4FF',
        icon: '📷',
        bodyHtml: '''
          <p>Hola <strong>${user.nombre}</strong>, bienvenido al sistema de vigilancia inteligente.</p>
          <p>Tu cuenta ha sido creada exitosamente el <strong>${_formatDate(user.fechaRegistro)}</strong>.</p>
          <div style="background:#0D1120;border-radius:12px;padding:20px;margin:24px 0;border-left:4px solid #00D4FF;">
            <p style="color:#00D4FF;margin:0 0 8px 0;font-weight:bold;">📋 Resumen de tu cuenta</p>
            <p style="color:#ccc;margin:4px 0;font-size:13px;">• Email: ${user.email}</p>
            <p style="color:#ccc;margin:4px 0;font-size:13px;">• Sistema: ANPR Multi-Lane v2.0</p>
            <p style="color:#ccc;margin:4px 0;font-size:13px;">• Estado: ✅ Activa y protegida</p>
          </div>
          <p style="color:#888;font-size:12px;">Recuerda configurar tus alertas de detección en la pantalla de Ajustes.</p>
        ''',
      ),
    );
  }

  // ─── Correo de alerta de detección ────────────────────────────────────
  static Future<bool> sendDetectionAlertEmail({
    required UserModel user,
    required String placaDetectada,
    required String placaBd,
    required double similitud,
    required DateTime timestamp,
  }) async {
    if (user.gmailEmail == null || user.gmailAppPassword == null) {
      print('Sin SMTP — simulando alerta de detección a ${user.email}');
      return true;
    }
    final simStr = '${(similitud * 100).toStringAsFixed(1)}%';
    return _send(
      smtpEmail: user.gmailEmail!,
      smtpPassword: user.gmailAppPassword!,
      toEmail: user.email,
      subject: '🚨 ALERTA: Placa Robada Detectada — $placaDetectada',
      htmlBody: _templateBase(
        title: '⚠️ Vehículo Robado Detectado',
        accentColor: '#FF3D57',
        icon: '🚨',
        bodyHtml: '''
          <p>Hola <strong>${user.nombre}</strong>,</p>
          <p>El sistema detectó una placa coincidente con tu base de datos de vehículos robados.</p>
          <div style="background:#1A0A0D;border-radius:12px;padding:24px;margin:24px 0;border:1px solid #FF3D57;">
            <table style="width:100%;border-collapse:collapse;">
              <tr><td style="color:#888;padding:6px 0;font-size:13px;">📍 Placa Detectada</td>
                  <td style="color:#FF3D57;font-size:20px;font-family:monospace;font-weight:bold;letter-spacing:4px;">$placaDetectada</td></tr>
              <tr><td style="color:#888;padding:6px 0;font-size:13px;">🗄️ Coincide con BD</td>
                  <td style="color:#fff;font-family:monospace;font-size:16px;letter-spacing:2px;">$placaBd</td></tr>
              <tr><td style="color:#888;padding:6px 0;font-size:13px;">📊 Similitud</td>
                  <td style="color:#FFB300;font-weight:bold;">$simStr</td></tr>
              <tr><td style="color:#888;padding:6px 0;font-size:13px;">🕐 Hora</td>
                  <td style="color:#ccc;">${_formatDate(timestamp)}</td></tr>
            </table>
          </div>
          <p style="color:#888;font-size:12px;">Revisa el sistema para más detalles. Si esto es una falsa alarma, puedes ajustar el umbral de detección en Ajustes.</p>
        ''',
      ),
    );
  }

  // ─── Plantilla base de correo ─────────────────────────────────────────
  static String _templateBase({
    required String title,
    required String accentColor,
    required String icon,
    required String bodyHtml,
  }) {
    return '''
      <!DOCTYPE html>
      <html>
      <body style="margin:0;padding:0;background-color:#0D1117;font-family:'Segoe UI',Arial,sans-serif;">
        <div style="max-width:600px;margin:40px auto;background:#111827;border-radius:16px;overflow:hidden;border:1px solid #1F2937;">
          <div style="background:linear-gradient(135deg,#0D1120,#1A2035);padding:32px;text-align:center;border-bottom:1px solid $accentColor;">
            <div style="font-size:48px;margin-bottom:12px;">$icon</div>
            <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">$title</h1>
            <p style="color:$accentColor;margin:6px 0 0 0;font-size:12px;letter-spacing:3px;font-family:monospace;">ALERTA VECINAL · ANPR SYSTEM</p>
          </div>
          <div style="padding:32px;color:#ccc;line-height:1.6;font-size:14px;">
            $bodyHtml
          </div>
          <div style="background:#0D1120;padding:16px;text-align:center;border-top:1px solid #1F2937;">
            <p style="color:#555;font-size:11px;margin:0;">© ${DateTime.now().year} Alerta Vecinal · Sistema de Vigilancia Inteligente</p>
          </div>
        </div>
      </body>
      </html>
    ''';
  }

  static String _formatDate(DateTime dt) {
    return '${dt.day.toString().padLeft(2,'0')}/${dt.month.toString().padLeft(2,'0')}/${dt.year}  ${dt.hour.toString().padLeft(2,'0')}:${dt.minute.toString().padLeft(2,'0')}';
  }

  // ─── Enviador SMTP central ────────────────────────────────────────────
  static Future<bool> _send({
    required String smtpEmail,
    required String smtpPassword,
    required String toEmail,
    required String subject,
    required String htmlBody,
  }) async {
    final smtpServer = gmail(smtpEmail, smtpPassword);
    final message = Message()
      ..from = Address(smtpEmail, 'Alerta Vecinal')
      ..recipients.add(toEmail)
      ..subject = subject
      ..html = htmlBody;
    try {
      await send(message, smtpServer);
      return true;
    } catch (e) {
      print('Error SMTP Gmail: $e');
      return false;
    }
  }
}



