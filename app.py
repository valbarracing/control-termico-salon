from datetime import datetime
import math
import requests
from zoneinfo import ZoneInfo
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Control Térmico Salón", page_icon="🌡️", layout="centered"
)

# Auto-refresco en el navegador cada 5 minutos (300,000 ms)
st.html(
    "<script>setTimeout(function(){ window.location.reload(); }, 300000);</script>"
)


def obtener_hora_lima():
    return datetime.now(ZoneInfo("America/Lima")).hour


@st.cache_data(ttl=300)
def obtener_datos():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -12.0464,
        "longitude": -77.0428,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature",
        "timezone": "America/Lima",
    }
    hora = obtener_hora_lima()
    try:
        r = requests.get(
            url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        if r.status_code == 200:
            cur = r.json().get("current", {})
            return (
                cur.get("temperature_2m", 23.0),
                cur.get("apparent_temperature", 23.0),
                cur.get("relative_humidity_2m", 80.0),
                hora,
            )
    except Exception:
        pass
    return 23.0, 23.0, 80.0, hora


def mround(val, base=0.5):
    return round(val / base) * base


def calcular(temp_amb, sens_term, humedad, hora):
    # Matriz Excel V2.0
    b7 = 0.45 * temp_amb + 0.55 * sens_term
    b8 = sorted([0.85, 1.5, 1 + 0.025 * (humedad - 80)])[1]
    b9 = 21 + (b7 - 21) * b8
    raw_b10 = (
        22.5
        + 3 * math.tanh((b9 - 21) / 7)
        - 0.7 * math.cos(2 * math.pi * (hora - 15) / 24)
    )
    b10 = sorted([16.0, 30.0, mround(raw_b10, 0.5)])[1]

    if b9 < 19 and (b9 - b10) < -2:
        modo = "HEAT"
    elif abs(b9 - b10) <= 2 and humedad >= 82 and b9 >= 19:
        modo = "DRY"
    elif (b9 - b10) > 1.5:
        modo = "COOL"
    else:
        modo = "AUTO"

    return f"{modo} {b10:g}"


# Interfaz Streamlit
st.title("🌡️ Control Térmico del Salón")
st.caption("Matriz de Automatización V2.0 en Python")

temp_amb, sens_term, humedad, hora = obtener_datos()
config = calcular(temp_amb, sens_term, humedad, hora)

st.subheader("Configuración Recomendada del Aire")
st.info(f"### ⚙️ **{config}**")

st.markdown("---")
st.subheader("📊 Clima Actual en Lima")

col1, col2 = st.columns(2)
col1.metric("Temperatura Ambiente", f"{temp_amb} °C")
col2.metric("Sensación Térmica", f"{sens_term} °C")

col3, col4 = st.columns(2)
col3.metric("Humedad Relativa", f"{humedad} %")
col4.metric("Hora Evaluada", f"{hora}:00 hrs")

st.markdown("---")
hora_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%H:%M:%S")
st.caption(f"Última actualización: {hora_actual} (Hora de Lima)")

if st.button("🔄 Actualizar Datos Ahora"):
    st.cache_data.clear()
    st.rerun()
