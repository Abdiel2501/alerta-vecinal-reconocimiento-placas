"""
setup_db.py — Menú interactivo para administrar la base de datos de placas robadas.

Uso:
    python setup_db.py
"""

from database import DatabasePlacas
from datetime import datetime


def imprimir_tabla(placas: list):
    """Imprime las placas en formato de tabla."""
    if not placas:
        print("\n  (No hay registros)\n")
        return

    print(f"\n{'─'*90}")
    print(f"  {'ID':<5} {'PLACA':<12} {'MODELO':<20} {'COLOR':<12} {'PROPIETARIO':<20} {'FECHA':<12} {'ESTADO'}")
    print(f"{'─'*90}")
    for p in placas:
        estado = "✅ ACTIVO" if p["activo"] else "❌ INACTIVO"
        print(f"  {p['id']:<5} {p['placa']:<12} {p['modelo']:<20} {p['color']:<12} {p['propietario']:<20} {p['fecha_reporte']:<12} {estado}")
    print(f"{'─'*90}\n")


def menu_agregar(db: DatabasePlacas):
    """Flujo interactivo para agregar una placa."""
    print("\n── AGREGAR NUEVA PLACA ROBADA ──")
    placa       = input("  Placa (ej: ABC1234):           ").strip().upper()
    modelo      = input("  Modelo (ej: Toyota Corolla):   ").strip()
    color       = input("  Color (ej: Blanco):            ").strip()
    propietario = input("  Propietario:                   ").strip()
    fecha       = input(f"  Fecha del reporte (AAAA-MM-DD, Enter={datetime.now().strftime('%Y-%m-%d')}): ").strip()
    descripcion = input("  Descripción del robo:          ").strip()

    if not placa:
        print("❌ La placa no puede estar vacía.")
        return

    db.agregar_placa(
        placa=placa,
        modelo=modelo,
        color=color,
        propietario=propietario,
        fecha_reporte=fecha or None,
        descripcion=descripcion
    )


def menu_eliminar(db: DatabasePlacas):
    """Flujo para desactivar una placa (vehículo recuperado)."""
    print("\n── DESACTIVAR PLACA (Vehículo Recuperado) ──")
    placa = input("  Placa a desactivar: ").strip().upper()
    if placa:
        db.eliminar_placa(placa)
    else:
        print("❌ Placa inválida.")


def menu_historial(db: DatabasePlacas):
    """Muestra el historial de alertas."""
    historial = db.listar_historial(limite=20)
    print(f"\n── HISTORIAL DE ALERTAS (últimas {len(historial)}) ──")
    if not historial:
        print("  (Sin alertas registradas aún)\n")
        return

    print(f"\n{'─'*80}")
    print(f"  {'PLACA BD':<12} {'DETECTADA':<12} {'SIMILITUD':<12} {'FECHA'}")
    print(f"{'─'*80}")
    for h in historial:
        sim = f"{h['similitud']*100:.1f}%" if h['similitud'] and h['similitud'] <= 1 else f"{h['similitud']}%"
        print(f"  {h['placa']:<12} {h['placa_detectada']:<12} {sim:<12} {h['fecha_alerta']}")
    print(f"{'─'*80}\n")


def menu_usuarios(db: DatabasePlacas):
    """Menú interactivo para gestionar usuarios de Telegram."""
    while True:
        print("\n── GESTIÓN DE USUARIOS DE TELEGRAM ──")
        print("  1. 👥 Ver todos los usuarios")
        print("  2. ➕ Registrar nuevo usuario")
        print("  3. ❌ Desactivar usuario")
        print("  0. ⬅️ Volver al menú principal")
        
        op = input("\n  Opción: ").strip()
        if op == "1":
            usuarios = db.listar_usuarios(solo_activos=False)
            if not usuarios:
                print("  (No hay usuarios registrados)\n")
            else:
                print(f"\n{'─'*60}")
                print(f"  {'ID':<5} {'NOMBRE':<20} {'CHAT ID':<20} {'ESTADO'}")
                print(f"{'─'*60}")
                for u in usuarios:
                    estado = "✅ ACTIVO" if u["activo"] else "❌ INACTIVO"
                    print(f"  {u['id']:<5} {u['nombre']:<20} {u['telegram_chat_id']:<20} {estado}")
                print(f"{'─'*60}\n")
        elif op == "2":
            nombre = input("  Nombre del usuario: ").strip()
            chat_id = input("  Telegram Chat ID: ").strip()
            if nombre and chat_id:
                db.agregar_usuario(nombre, chat_id)
            else:
                print("❌ Nombre o Chat ID inválidos.")
        elif op == "3":
            chat_id = input("  Telegram Chat ID a desactivar: ").strip()
            if chat_id:
                db.eliminar_usuario(chat_id)
        elif op == "0":
            break
        else:
            print("  ⚠️ Opción no válida.")


def main():
    print("=" * 55)
    print("  🔒 SISTEMA DE GESTIÓN DE PLACAS ROBADAS")
    print("=" * 55)

    db = DatabasePlacas()

    while True:
        print("\n  MENÚ PRINCIPAL")
        print("  ─────────────────────────────")
        print("  1. 📋 Ver placas robadas activas")
        print("  2. ➕ Agregar placa robada")
        print("  3. ✅ Desactivar placa (recuperada)")
        print("  4. 📜 Ver historial de alertas")
        print("  5. 🔍 Consultar una placa manualmente")
        print("  6. 📊 Ver todas las placas (activas e inactivas)")
        print("  7. 👥 Gestionar usuarios de Telegram")
        print("  0. 🚪 Salir")
        print()

        opcion = input("  Opción: ").strip()

        if opcion == "1":
            placas = db.listar_placas(solo_activas=True)
            print(f"\n── {len(placas)} PLACAS ROBADAS ACTIVAS ──")
            imprimir_tabla(placas)

        elif opcion == "2":
            menu_agregar(db)

        elif opcion == "3":
            menu_eliminar(db)

        elif opcion == "4":
            menu_historial(db)

        elif opcion == "5":
            placa_consulta = input("\n  Placa a consultar: ").strip().upper()
            es_robado, info = db.consultar_placa(placa_consulta)
            if es_robado:
                sim = info.get("similitud", 100)
                sim_str = f"({sim}% similitud)" if isinstance(sim, float) and sim < 100 else "(coincidencia exacta)"
                print(f"\n  🚨 ¡PLACA ROBADA! {sim_str}")
                print(f"     Vehículo:    {info['modelo']} — {info['color']}")
                print(f"     Propietario: {info['propietario']}")
                print(f"     Reportado:   {info['fecha_reporte']}")
                print(f"     Descripción: {info.get('descripcion', 'N/A')}\n")
            else:
                print(f"\n  ✅ La placa '{placa_consulta}' NO tiene reporte de robo.\n")

        elif opcion == "6":
            placas = db.listar_placas(solo_activas=False)
            print(f"\n── TODAS LAS PLACAS ({len(placas)} registros) ──")
            imprimir_tabla(placas)

        elif opcion == "7":
            menu_usuarios(db)

        elif opcion == "0":
            print("\n  Hasta luego. 👋\n")
            break
        else:
            print("  ⚠️  Opción no válida.")


if __name__ == "__main__":
    main()
