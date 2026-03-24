"""
CRUD — Auditoría
Consultas de solo lectura sobre la tabla auditoria.
Los logs son INMUTABLES — no hay UPDATE ni DELETE aquí.
"""
import csv
import io
from app.core.database import get_db_connection


def consultar_logs(
    usuario: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    modulo: str = None,
    accion: str = None,
    page: int = 1,
    per_page: int = 50
) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        condiciones = []
        params = []

        if usuario:
            condiciones.append("u.usuario LIKE ?")
            params.append(f"%{usuario}%")
        if fecha_desde:
            condiciones.append("a.fecha_accion >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("a.fecha_accion <= ?")
            params.append(fecha_hasta + " 23:59:59")
        if modulo:
            condiciones.append("a.modulo = ?")
            params.append(modulo)
        if accion:
            condiciones.append("a.accion LIKE ?")
            params.append(f"%{accion}%")

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        cur.execute(
            f"SELECT COUNT(*) FROM auditoria a LEFT JOIN usuarios u ON a.usuario_id = u.id {where}",
            params
        )
        total = cur.fetchone()[0]

        offset = (page - 1) * per_page
        cur.execute(f"""
            SELECT a.id, a.fecha_accion, a.accion, a.modulo, a.detalle,
                   a.ip_origen, u.usuario, u.nombre_completo
            FROM auditoria a
            LEFT JOIN usuarios u ON a.usuario_id = u.id
            {where}
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

        items = [dict(r) for r in cur.fetchall()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page))
        }
    finally:
        cur.close()
        conn.close()


def exportar_logs_csv(
    usuario: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    modulo: str = None,
    accion: str = None
) -> str:
    """Genera un CSV con todos los logs que coincidan con los filtros."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        condiciones = []
        params = []

        if usuario:
            condiciones.append("u.usuario LIKE ?")
            params.append(f"%{usuario}%")
        if fecha_desde:
            condiciones.append("a.fecha_accion >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("a.fecha_accion <= ?")
            params.append(fecha_hasta + " 23:59:59")
        if modulo:
            condiciones.append("a.modulo = ?")
            params.append(modulo)
        if accion:
            condiciones.append("a.accion LIKE ?")
            params.append(f"%{accion}%")

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

        cur.execute(f"""
            SELECT a.id, a.fecha_accion, u.usuario, u.nombre_completo,
                   a.accion, a.modulo, a.detalle, a.ip_origen
            FROM auditoria a
            LEFT JOIN usuarios u ON a.usuario_id = u.id
            {where}
            ORDER BY a.id DESC
        """, params)

        filas = cur.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Fecha", "Usuario", "Nombre", "Acción", "Módulo", "Detalle", "IP Origen"])
        for fila in filas:
            writer.writerow(list(fila))

        return output.getvalue()
    finally:
        cur.close()
        conn.close()
