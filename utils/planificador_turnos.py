from datetime import datetime, timedelta

def obtener_hueco_libre(ocupado, inicio_dt, fin_dt, duracion):
    bloques = sorted(ocupado, key=lambda x: x["inicio"])
    actual = inicio_dt

    for bloque in bloques:
        if actual + timedelta(minutes=duracion) <= bloque["inicio"]:
            return actual
        actual = max(actual, bloque["fin"])

    if actual + timedelta(minutes=duracion) <= fin_dt:
        return actual

    return None

def tiempo_desplazamiento(origen, destino, ciudad, tiempos):
    if origen == destino:
        return 0
    clave1 = f"{origen}-{destino}"
    clave2 = f"{destino}-{origen}"
    return tiempos.get(ciudad, {}).get(clave1) or tiempos.get(ciudad, {}).get(clave2) or 9999

def planificar_turnos(hoteles, empleados, cargas, fecha_str, tiempos):
    asignaciones = []
    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")

    hoteles_dict = {h["nombre"]: h for h in hoteles}
    dias_traducidos = {
        "monday": "lunes",
        "tuesday": "martes",
        "wednesday": "miércoles",
        "thursday": "jueves",
        "friday": "viernes",
        "saturday": "sábado",
        "sunday": "domingo"
    }
    dia_semana = dias_traducidos[fecha_dt.strftime("%A").lower()]

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
        duracion_total = carga["duracion_min"]
        ciudad = hoteles_dict[hotel]["ciudad"]
        hora_min_inicio = datetime.strptime(f"{fecha_str} {hoteles_dict[hotel]['hora_min_inicio']}", "%Y-%m-%d %H:%M")

        posibles = [e for e in empleados_disponibles if e["ciudad"] == ciudad]
        posibles.sort(key=lambda e: (
            tiempo_desplazamiento(
                e["ocupado"][-1]["hotel"] if e["ocupado"] else hotel,
                hotel,
                ciudad,
                tiempos
            ),
            e["prioridad_hoteles"].get(hotel, 999)
        ))

        asignado = False

        for emp in posibles:
            ultimo_bloque = emp["ocupado"][-1] if emp["ocupado"] else None
            hotel_anterior = ultimo_bloque["hotel"] if ultimo_bloque else hotel
            tiempo_extra = tiempo_desplazamiento(hotel_anterior, hotel, ciudad, tiempos)
            inicio_busqueda = max(emp["inicio_dt"], hora_min_inicio)

            if emp.get("requiere_acompanamiento", False):
                acomp = next((
                    e2 for e2 in posibles
                    if e2 != emp and not e2.get("requiere_acompanamiento", False)
                ), None)
                if not acomp:
                    continue

                for dur_emp in range(duracion_total, 0, -15):
                    if dur_emp <= 15 or (duracion_total - dur_emp) <= 15:
                        continue
                    dur_acomp = duracion_total - dur_emp
                    emp_hueco = obtener_hueco_libre(emp["ocupado"], max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda), emp["fin_dt"], dur_emp + tiempo_extra)
                    acomp_hueco = obtener_hueco_libre(acomp["ocupado"], max(acomp["inicio_dt"], hora_min_inicio, acomp["ocupado"][-1]["fin"] if acomp["ocupado"] else inicio_busqueda), acomp["fin_dt"], dur_acomp + tiempo_extra)
                    if emp_hueco and acomp_hueco:
                        emp_inicio = emp_hueco + timedelta(minutes=tiempo_extra)
                        acomp_inicio = acomp_hueco + timedelta(minutes=tiempo_extra)

                        if tiempo_extra > 0:
                            emp["ocupado"].append({
                                "inicio": emp_hueco,
                                "fin": emp_inicio,
                                "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}"
                            })
                            acomp["ocupado"].append({
                                "inicio": acomp_hueco,
                                "fin": acomp_inicio,
                                "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}"
                            })

                        emp["ocupado"].append({"inicio": emp_inicio, "fin": emp_inicio + timedelta(minutes=dur_emp), "hotel": hotel})
                        acomp["ocupado"].append({"inicio": acomp_inicio, "fin": acomp_inicio + timedelta(minutes=dur_acomp), "hotel": hotel})

                        asignaciones.append({
                            "hotel": hotel,
                            "empleado": emp["nombre"],
                            "inicio": emp_inicio.strftime("%H:%M"),
                            "duracion": dur_emp,
                            "acompañado_por": acomp["nombre"]
                        })
                        asignaciones.append({
                            "hotel": hotel,
                            "empleado": acomp["nombre"],
                            "inicio": acomp_inicio.strftime("%H:%M"),
                            "duracion": dur_acomp,
                            "acompañado_por": emp["nombre"]
                        })
                        asignado = True
                        break
                if asignado:
                    break

            else:
                hueco = obtener_hueco_libre(emp["ocupado"], max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda), emp["fin_dt"], duracion_total + tiempo_extra)
                if not hueco:
                    continue

                inicio_real = hueco + timedelta(minutes=tiempo_extra)
                fin_asignacion = inicio_real + timedelta(minutes=duracion_total)

                if tiempo_extra > 0:
                    emp["ocupado"].append({
                        "inicio": hueco,
                        "fin": inicio_real,
                        "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}"
                    })

                emp["ocupado"].append({"inicio": inicio_real, "fin": fin_asignacion, "hotel": hotel})

                asignaciones.append({
                    "hotel": hotel,
                    "empleado": emp["nombre"],
                    "inicio": inicio_real.strftime("%H:%M"),
                    "duracion": duracion_total,
                    "acompañado_por": None
                })
                asignado = True
                break

        if not asignado:
            asignaciones.append({
                "hotel": hotel,
                "empleado": None,
                "inicio": None,
                "duracion": carga["duracion_min"],
                "acompañado_por": None,
                "nota": "No asignado por falta de disponibilidad"
            })

    return asignaciones
