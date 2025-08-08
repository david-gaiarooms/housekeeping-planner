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

def planificar_turnos(hoteles, empleados, cargas, fecha_str, tiempos, ciudad_objetivo=None):
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
    if ciudad_objetivo:
        empleados = [e for e in empleados if e["ciudad"] == ciudad_objetivo]
        hoteles = [h for h in hoteles if h["ciudad"] == ciudad_objetivo]
        cargas = [c for c in cargas if hoteles_dict.get(c["hotel"], {}).get("ciudad") == ciudad_objetivo]
        hoteles_dict = {h["nombre"]: h for h in hoteles}

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
            inicio_busqueda = max(emp["inicio_dt"], hora_min_inicio)

            if emp.get("requiere_acompanamiento", False):
                acomp = next((
                    e2 for e2 in posibles
                    if e2 != emp and not e2.get("requiere_acompanamiento", False)
                ), None)
                if not acomp:
                    continue

                for dur_emp in range(duracion_total, 0, -15):
                    hotel_anterior_emp = emp["ocupado"][-1]["hotel"] if emp["ocupado"] else None
                    hotel_anterior_acomp = acomp["ocupado"][-1]["hotel"] if acomp["ocupado"] else None

                    tiempo_extra_emp = tiempo_desplazamiento(hotel_anterior_emp, hotel, ciudad, tiempos) if hotel_anterior_emp else 0
                    tiempo_extra_acomp = tiempo_desplazamiento(hotel_anterior_acomp, hotel, ciudad, tiempos) if hotel_anterior_acomp else 0
                    if dur_emp <= 15 or (duracion_total - dur_emp) <= 15:
                        continue
                    dur_acomp = duracion_total - dur_emp
                    emp_hueco = obtener_hueco_libre(emp["ocupado"], max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda), emp["fin_dt"], dur_emp + tiempo_extra_emp)
                    acomp_hueco = obtener_hueco_libre(acomp["ocupado"], max(acomp["inicio_dt"], hora_min_inicio, acomp["ocupado"][-1]["fin"] if acomp["ocupado"] else inicio_busqueda), acomp["fin_dt"], dur_acomp + tiempo_extra_acomp)
                    if emp_hueco and acomp_hueco:
                        emp_inicio = emp_hueco + timedelta(minutes=tiempo_extra_emp)
                        acomp_inicio = acomp_hueco + timedelta(minutes=tiempo_extra_acomp)

                        if tiempo_extra_emp > 0 and hotel_anterior_emp != hotel:
                            emp["ocupado"].append({
                                "inicio": emp_hueco,
                                "fin": emp_inicio,
                                "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}"
                            })
                            acomp["ocupado"].append({
                            "inicio": acomp_hueco,
                            "fin": acomp_inicio,
                            "hotel": f"DESPLAZAMIENTO: {hotel_anterior_acomp} → {hotel}"
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
                ultimo_bloque = emp["ocupado"][-1] if emp["ocupado"] else None
                hotel_anterior = ultimo_bloque["hotel"] if ultimo_bloque else None
                tiempo_extra = tiempo_desplazamiento(hotel_anterior, hotel, ciudad, tiempos) if hotel_anterior else 0
                hueco = obtener_hueco_libre(emp["ocupado"], max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda), emp["fin_dt"], duracion_total + tiempo_extra)
                if not hueco:
                    tiempo_total_disponible = int((emp["fin_dt"] - max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda)).total_seconds() / 60)
                    if tiempo_total_disponible > 0 and (duracion_total - tiempo_total_disponible) >= 30:
                        minutos_usar = min(tiempo_total_disponible, duracion_total)
                        inicio_real = emp["fin_dt"] - timedelta(minutes=minutos_usar)
                        fin_asignacion = emp["fin_dt"]

                        if hotel_anterior != hotel and tiempo_extra > 0:
                            emp["ocupado"].append({
                                "inicio": inicio_real - timedelta(minutes=tiempo_extra),
                                "fin": inicio_real,
                                "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}",
                                "tipo": "Desplazamiento",
                                "color": "#B0B0B0"
                            })

                        emp["ocupado"].append({
                        "inicio": inicio_real - timedelta(minutes=tiempo_extra),
                        "fin": inicio_real,
                        "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}",
                        "tipo": "Desplazamiento",
                        "color": "#B0B0B0"
                    })

                if hotel_anterior != hotel and tiempo_extra > 0:
                            emp["ocupado"].append({
                                "inicio": inicio_real - timedelta(minutes=tiempo_extra),
                                "fin": inicio_real,
                                "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}",
                                "tipo": "Desplazamiento",
                                "color": "#B0B0B0"
                            })

                        emp["ocupado"].append({
                            "inicio": inicio_real,
                            "fin": fin_asignacion,
                            "hotel": hotel,
                            "tipo": "Tiempo extra",
                            "color": "#ff9999"
                        })
                        asignaciones.append({
                            "hotel": hotel,
                            "empleado": emp["nombre"],
                            "inicio": inicio_real.strftime("%H:%M"),
                            "duracion": minutos_usar,
                            "acompañado_por": None,
                            "nota": "Tiempo extra por límite de disponibilidad",
                            "tipo": "Tiempo extra"
                        })
                        duracion_total -= minutos_usar
                        if duracion_total <= 0:
                            asignado = True
                            break
                        continue
                    # Verificar si solo faltan menos de 30 minutos para completar
                    tiempo_total_disponible = int((emp["fin_dt"] - max(emp["inicio_dt"], hora_min_inicio, emp["ocupado"][-1]["fin"] if emp["ocupado"] else inicio_busqueda)).total_seconds() / 60)
                    if 0 < tiempo_total_disponible < duracion_total and (duracion_total - tiempo_total_disponible) < 30:
                        inicio_real = emp["fin_dt"] - timedelta(minutes=tiempo_total_disponible)
                        fin_asignacion = emp["fin_dt"]
                        emp["ocupado"].append({
                            "inicio": inicio_real,
                            "fin": fin_asignacion,
                            "hotel": hotel,
                            "tipo": "Tiempo extra",
                            "color": "#ff9999"
                        })
                        asignaciones.append({
                            "hotel": hotel,
                            "empleado": emp["nombre"],
                            "inicio": inicio_real.strftime("%H:%M"),
                            "duracion": tiempo_total_disponible,
                            "acompañado_por": None,
                            "nota": "Asignación parcial por margen menor a 30 min",
                            "tipo": "Tiempo extra"
                        })
                        asignado = True
                        break
                    continue

                if hotel_anterior != hotel and tiempo_extra > 0:
                    emp["ocupado"].append({
                        "inicio": hueco,
                        "fin": hueco + timedelta(minutes=tiempo_extra),
                        "hotel": f"DESPLAZAMIENTO: {hotel_anterior} → {hotel}",
                        "tipo": "Desplazamiento",
                        "color": "#B0B0B0"
                    })

                inicio_real = hueco + timedelta(minutes=tiempo_extra)
                fin_asignacion = inicio_real + timedelta(minutes=duracion_total)

                

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

    # Agregar visualización de capacidad no usada
    for emp in empleados_disponibles:
        total_min_disp = int((emp["fin_dt"] - emp["inicio_dt"]).total_seconds() / 60)
        ocupado_min = sum(int((b["fin"] - b["inicio"]).total_seconds() / 60) for b in emp["ocupado"])
        libre_min = total_min_disp - ocupado_min
        if libre_min > 0:
            emp["ocupado"].append({
                "inicio": emp["fin_dt"] - timedelta(minutes=libre_min),
                "fin": emp["fin_dt"],
                "hotel": f"NO USADO ({libre_min} min)",
                "color": "#ffcccc"
            })

        # Calcular resumen de tiempo total requerido y disponible
    resumen = {
        "porcentaje_desplazamiento": round(
            sum(
                int((b["fin"] - b["inicio"]).total_seconds() / 60)
                for e in empleados_disponibles for b in e["ocupado"]
                if b.get("tipo") == "Desplazamiento"
            ) / max(1, sum(int((e["fin_dt"] - e["inicio_dt"]).total_seconds() / 60) for e in empleados_disponibles)) * 100, 2
        ),
        "total_desplazamiento_min": sum(
            int((b["fin"] - b["inicio"]).total_seconds() / 60)
            for e in empleados_disponibles for b in e["ocupado"]
            if b.get("tipo") == "Desplazamiento"
        ),
        "total_carga_trabajo_min": sum(c["duracion_min"] for c in cargas),
        "total_disponible_min": sum(int((e["fin_dt"] - e["inicio_dt"]).total_seconds() / 60) for e in empleados_disponibles),
        "total_asignado_min": sum(
            int((b["fin"] - b["inicio"]).total_seconds() / 60)
            for e in empleados_disponibles for b in e["ocupado"]
            if not isinstance(b["hotel"], str) or not b["hotel"].startswith("NO USADO")
        ),
        "total_tiempo_extra_min": sum(
            int((b["fin"] - b["inicio"]).total_seconds() / 60)
            for e in empleados_disponibles for b in e["ocupado"]
            if isinstance(b.get("tipo"), str) and b["tipo"] == "Tiempo extra"
        )
    }

    return asignaciones, resumen
