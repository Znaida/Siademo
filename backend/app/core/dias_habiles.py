"""
T2.5.2 — Cálculo de días hábiles + festivos Colombia
Usa workalendar con calendario oficial colombiano (Ley Emiliani + festivos religiosos)
"""
from datetime import date, timedelta
from workalendar.america import Colombia

_cal = Colombia()


def agregar_dias_habiles(fecha_inicio: date, dias: int) -> date:
    """
    Dado una fecha de inicio y un número de días hábiles,
    retorna la fecha de vencimiento excluyendo fines de semana y festivos colombianos.
    """
    fecha = fecha_inicio
    dias_contados = 0
    while dias_contados < dias:
        fecha += timedelta(days=1)
        if _cal.is_working_day(fecha):
            dias_contados += 1
    return fecha


def dias_habiles_entre(fecha_inicio: date, fecha_fin: date) -> int:
    """
    Calcula cuántos días hábiles hay entre dos fechas (excluyendo inicio, incluyendo fin).
    """
    if fecha_fin <= fecha_inicio:
        return 0
    count = 0
    fecha = fecha_inicio
    while fecha < fecha_fin:
        fecha += timedelta(days=1)
        if _cal.is_working_day(fecha):
            count += 1
    return count


def calcular_semaforo(fecha_vencimiento: date, dias_totales: int) -> dict:
    """
    Calcula el semáforo SLA de un radicado.
    Retorna color, días restantes y porcentaje consumido.
    """
    hoy = date.today()

    if fecha_vencimiento < hoy:
        dias_vencido = dias_habiles_entre(fecha_vencimiento, hoy)
        return {
            "color": "rojo",
            "emoji": "🔴",
            "dias_restantes": -dias_vencido,
            "mensaje": f"Vencido hace {dias_vencido} día(s) hábil(es)",
            "porcentaje_consumido": 100
        }

    dias_restantes = dias_habiles_entre(hoy, fecha_vencimiento)
    dias_consumidos = dias_totales - dias_restantes
    porcentaje = round((dias_consumidos / dias_totales) * 100) if dias_totales > 0 else 0

    if fecha_vencimiento == hoy:
        return {
            "color": "rojo",
            "emoji": "🔴",
            "dias_restantes": 0,
            "mensaje": "Vence hoy",
            "porcentaje_consumido": 100
        }
    elif porcentaje >= 70:
        return {
            "color": "amarillo",
            "emoji": "🟡",
            "dias_restantes": dias_restantes,
            "mensaje": f"Vence en {dias_restantes} día(s) hábil(es)",
            "porcentaje_consumido": porcentaje
        }
    else:
        return {
            "color": "verde",
            "emoji": "🟢",
            "dias_restantes": dias_restantes,
            "mensaje": f"Vence en {dias_restantes} día(s) hábil(es)",
            "porcentaje_consumido": porcentaje
        }


def es_dia_habil(fecha: date) -> bool:
    return _cal.is_working_day(fecha)


def festivos_anio(anio: int) -> list:
    """Retorna lista de festivos colombianos para un año dado."""
    return [
        {"fecha": str(f), "nombre": nombre}
        for f, nombre in _cal.holidays(anio)
    ]
