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
            asignaciones = planificar_turnos(
                hoteles=hoteles,
                empleados=empleados,
                cargas=cargas_filtradas,
                fecha_str=fecha_seleccionada.isoformat(),
                tiempos=tiempos
            )

            st.success("✅ Planificación realizada")

            # Tabla por empleado (desde ocupado)
            st.subheader("📋 Turnos por empleado (incluye desplazamientos)")
            for empleado in empleados:
                st.markdown(f"### 🧑‍💼 {empleado['nombre']}")
                if "ocupado" in empleado and empleado["ocupado"]:
                    df_emp = pd.DataFrame(empleado["ocupado"])
                    df_emp["tipo"] = df_emp["hotel"].apply(
                        lambda h: "Desplazamiento" if isinstance(h, str) and h.startswith("DESPLAZAMIENTO") else "Limpieza"
                    )
                    df_emp = df_emp.sort_values("inicio")
                    st.dataframe(df_emp[["inicio", "fin", "hotel", "tipo"]])
                else:
                    st.write("Sin asignaciones.")

            # Timeline visual
            st.subheader("📊 Línea de tiempo con desplazamientos destacados")

            ocupaciones = []
            for e in empleados:
                if "ocupado" in e:
                    for b in e["ocupado"]:
                        ocupaciones.append({
                            "empleado": e["nombre"],
                            "hotel": b["hotel"],
                            "start": b["inicio"],
                            "end": b["fin"],
                            "tipo": "Desplazamiento" if isinstance(b["hotel"], str) and b["hotel"].startswith("DESPLAZAMIENTO") else "Limpieza"
                        })

            df_timeline = pd.DataFrame(ocupaciones)
            df_timeline["tarea"] = df_timeline["hotel"]

            color_map = {
                "Desplazamiento": "#B0B0B0",  # gris claro
                "Limpieza": "#1f77b4"         # azul base
            }

            fig = px.timeline(
                df_timeline,
                x_start="start",
                x_end="end",
                y="empleado",
                color="tipo",
                text="tarea",
                color_discrete_map=color_map
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title="🕒 Línea de tiempo con limpieza y desplazamientos", height=600)
            st.plotly_chart(fig, use_container_width=True)

            # Exportar resultado
            st.subheader("⬇️ Descargar planificación")
            df_export = pd.DataFrame(asignaciones)
            st.download_button(
                "Descargar como CSV",
                df_export.to_csv(index=False).encode("utf-8"),
                "planificacion.csv",
                "text/csv"
            )
