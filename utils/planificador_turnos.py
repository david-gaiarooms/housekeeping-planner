from datetime import datetime, timedelta

def tiempo_desplazamiento(origen, destino, ciudad, tiempos):
    if origen == destino:
        return 0
    clave1 = f"{origen}-{destino}"
    clave2 = f"{destino}-{origen}"
    return tiempos.get(ciudad, {}).get(clave1) or tiempos.get(ciudad, {}).get(clave2) or 9999

def obtener_siguiente_inicio_libre(empleado, duracion, fecha, desde):
    bloques = sorted(empleado["ocupado"], key=lambda x: x["inicio"])
    hora_actual = max(empleado["inicio_dt"], desde)

    for bloque in bloques:
        if hora_actual + timedelta(minutes=duracion) <= bloque["inicio"]:
            return hora_actual
        hora_actual = max(hora_actual, bloque["fin"])

    if hora_actual + timedelta(minutes=duracion) <= empleado["fin_dt"]:
        return hora_actual

    return None

def planificar_turnos(hoteles, empleados, cargas, fecha_str, tiempos):
    asignaciones = []
    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")

    hoteles_dict = {h["nombre"]: h for h in hoteles}
    dia_semana = fecha_dt.strftime("%A").lower()

    empleados_disponibles = []
    for e in empleados:
        if dia_semana in e["horas_trabajo"]:
            inicio_str, fin_str = e["horas_trabajo"][dia_semana]
            inicio_dt = datetime.strptime(f"{fecha_str} {inicio_str}", "%Y-%m-%d %H:%M")
            fin_dt = datetime.strptime(f"{fecha_str} {fin_str}", "%Y-%m-%d %H:%M")
            e.update({
                "inicio_dt": inicio_dt,
                "fin_dt": fin_dt,
                "ocupado": []
            })
            empleados_disponibles.append(e)

    for carga in cargas:
        hotel = carga["hotel"]
        duracion_restante = carga["duracion_min"]
        ciudad = hoteles_dict[hotel]["ciudad"]
        hora_min_inicio = datetime.strptime(f"{fecha_str} {hoteles_dict[hotel]['hora_min_inicio']}", "%Y-%m-%d %H:%M")

        while duracion_restante > 0:
            posibles = [e for e in empleados_disponibles if e["ciudad"] == ciudad]
            posibles.sort(key=lambda e: e["prioridad_hoteles"].get(hotel, 999))

            asignado = False

            for emp in posibles:
                ultima_tarea = emp["ocupado"][-1] if emp["ocupado"] else None
                anterior = ultima_tarea["hotel"] if ultima_tarea else hotel
                desde = ultima_tarea["fin"] if ultima_tarea else hora_min_inicio

                desplazamiento = tiempo_desplazamiento(anterior, hotel, ciudad, tiempos)
                inicio_posible = obtener_siguiente_inicio_libre(emp, duracion_restante, fecha_dt, desde + timedelta(minutes=desplazamiento))

                if inicio_posible:
                    tiempo_disponible = (emp["fin_dt"] - inicio_posible).total_seconds() / 60
                    duracion_asignada = min(duracion_restante, tiempo_disponible)

                    if emp.get("requiere_acompanamiento", False):
                        acomp = next(
                            (e2 for e2 in posibles if e2 != emp and not e2["requiere_acompanamiento"] and obtener_siguiente_inicio_libre(e2, duracion_asignada, fecha_dt, desde + timedelta(minutes=desplazamiento))),
                            None
                        )
                        if not acomp:
                            continue
                        acomp_inicio = obtener_siguiente_inicio_libre(acomp, duracion_asignada, fecha_dt, desde + timedelta(minutes=desplazamiento))
                        acomp["ocupado"].append({
                            "inicio": acomp_inicio,
                            "fin": acomp_inicio + timedelta(minutes=duracion_asignada),
                            "hotel": hotel
                        })

                    emp["ocupado"].append({
                        "inicio": inicio_posible,
                        "fin": inicio_posible + timedelta(minutes=duracion_asignada),
                        "hotel": hotel
                    })

                    asignaciones.append({
                        "hotel": hotel,
                        "empleado": emp["nombre"],
                        "inicio": inicio_posible.strftime("%H:%M"),
                        "duracion": duracion_asignada,
                        "acompañado_por": acomp["nombre"] if emp.get("requiere_acompanamiento", False) else None
                    })

                    duracion_restante -= duracion_asignada
                    asignado = True
                    break

            if not asignado:
                asignaciones.append({
                    "hotel": hotel,
                    "empleado": None,
                    "inicio": None,
                    "duracion": duracion_restante,
                    "nota": "No asignado por falta de disponibilidad"
                })
                break

    return asignaciones
