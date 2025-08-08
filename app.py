import streamlit as st
import pandas as pd
import json
from datetime import date
from utils.planificador_turnos import planificar_turnos
import plotly.express as px

st.set_page_config(page_title="Planificador de Turnos", layout="wide")
st.title("🧹 Planificador de turnos - Limpieza de hoteles")

# Cargar datos base
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

hoteles = load_json("data/hoteles.json")
tiempos = load_json("data/tiempos_desplazamiento.json")
empleados = load_json("data/empleados.json")

# Subida de carga de trabajo
st.subheader("📤 Subir carga de trabajo (CSV o JSON)")
archivo_carga = st.file_uploader("Archivo:", type=["csv", "json"])
cargas = []

if archivo_carga:
    if archivo_carga.type == "application/json":
        cargas = json.load(archivo_carga)
    elif archivo_carga.type == "text/csv":
        df = pd.read_csv(archivo_carga)
        cargas = df.to_dict(orient="records")
    st.success(f"Se cargaron {len(cargas)} registros.")
else:
    st.info("Por favor, sube un archivo con la carga de trabajo para continuar.")

# Selección de ciudad
st.subheader("🏙️ Selecciona la ciudad a planificar")
ciudades_disponibles = sorted(set(h["ciudad"] for h in hoteles))
ciudad_seleccionada = st.selectbox("Ciudad", ciudades_disponibles)

# Planificación
if cargas:
    st.subheader("📅 Selecciona una fecha para planificar")
    fecha_seleccionada = st.date_input("Fecha", value=date.today())

    cargas_filtradas = [
        carga for carga in cargas if carga["fecha"] == fecha_seleccionada.isoformat()
    ]

    if not cargas_filtradas:
        st.warning("No hay carga de trabajo para la fecha seleccionada.")
    else:
        st.write(f"Cargas para el {fecha_seleccionada.isoformat()}:")
        st.dataframe(pd.DataFrame(cargas_filtradas))

        if st.button("🚀 Ejecutar planificación"):
            asignaciones, resumen = planificar_turnos(
                hoteles=hoteles,
                empleados=empleados,
                cargas=cargas_filtradas,
                fecha_str=fecha_seleccionada.isoformat(),
                tiempos=tiempos,
                ciudad_objetivo=ciudad_seleccionada
            )

            st.success("✅ Planificación realizada")

            # 🔍 Tabla resumen de disponibilidad, carga asignada y tiempo extra
            st.subheader("📊 Resumen de planificación para la ciudad")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("⏳ Tiempo total disponible", f"{resumen['total_disponible_min']} min")
            col2.metric("✅ Tiempo total asignado", f"{resumen['total_asignado_min']} min")
            col3.metric("🟥 Tiempo extra utilizado", f"{resumen['total_tiempo_extra_min']} min")
            col4.metric("📦 Carga total a cubrir", f"{resumen['total_carga_trabajo_min']} min")

            # Tabla por empleado (desde ocupado)
            st.subheader("📋 Turnos por empleado (incluye desplazamientos y no usado)")
            for empleado in empleados:
                st.markdown(f"### 🧑‍💼 {empleado['nombre']} — {ciudad_seleccionada}")
                if "ocupado" in empleado and empleado["ocupado"]:
                    df_emp = pd.DataFrame(empleado["ocupado"])
                    df_emp["tipo"] = df_emp["hotel"].apply(
                        lambda h: (
                            "Desplazamiento" if isinstance(h, str) and h.startswith("DESPLAZAMIENTO")
                            else "No usado" if isinstance(h, str) and h.startswith("NO USADO")
                            else "Tiempo extra" if "Tiempo extra" in str(h)
                            else "Limpieza"
                        )
                    )

                    df_emp = df_emp.sort_values("inicio")
                    st.dataframe(df_emp[["inicio", "fin", "hotel", "tipo"]])
                else:
                    st.write("Sin asignaciones.")

            # Timeline visual con colores personalizados
            st.subheader("📊 Línea de tiempo con desplazamientos, tiempo extra y capacidad no usada")

            ocupaciones = []
            for e in empleados:
                if "ocupado" in e:
                    for b in e["ocupado"]:
                        tipo = (
                            "Desplazamiento" if isinstance(b["hotel"], str) and b["hotel"].startswith("DESPLAZAMIENTO")
                            else "No usado" if isinstance(b["hotel"], str) and b["hotel"].startswith("NO USADO")
                            else "Tiempo extra" if b.get("tipo") == "Tiempo extra"
                            else "Limpieza"
                        )
                        ocupaciones.append({
                            "empleado": e["nombre"],
                            "hotel": b["hotel"],
                            "start": b["inicio"],
                            "end": b["fin"],
                            "tarea": b["hotel"],
                            "tipo": tipo
                        })

            df_timeline = pd.DataFrame(ocupaciones)

            fig = px.timeline(
                df_timeline,
                x_start="start",
                x_end="end",
                y="empleado",
                color="tipo",
                text="tarea",
                color_discrete_map={
                    "Limpieza": "#1f77b4",
                    "Desplazamiento": "#B0B0B0",
                    "No usado": "#ffcccc",
                    "Tiempo extra": "#ff9999"
                }
            )

            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                title=f"🕒 Línea de tiempo: limpieza, desplazamientos, tiempo extra y no usado — {ciudad_seleccionada}",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

            # Exportar resultado
            st.subheader("⬇️ Descargar planificación")
            df_export = pd.DataFrame(asignaciones)
            df_export["ciudad"] = ciudad_seleccionada
            st.dataframe(df_export)
            st.download_button(
                "Descargar como CSV",
                df_export.to_csv(index=False).encode("utf-8"),
                "planificacion.csv",
                "text/csv"
            )
