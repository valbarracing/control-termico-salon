from datetime import datetime, timezone, timedelta
import math
import requests
import streamlit as st

st.set_page_config(page_title="Control Térmico Salón", page_icon="🌡️", layout="centered")

st.html("<script>setTimeout(function(){ window.location.reload(); }, 300000);</script>")

LIMA_TZ = timezone(timedelta(hours=-5))

def obtener_tiempo_lima():
    return datetime.now(timezone.utc).astimezone(LIMA_TZ)

@st.cache_data(ttl=180)
def obtener_datos():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -12.0464,
        "longitude": -77.0428,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature",
        "timezone": "America/Lima",
    }
    ahora_lima = obtener_tiempo_lima()
    # Hora con precisión decimal (ej: 11:30 -> 11.5)
    hora_exacta = ahora_lima.hour + (ahora_lima.minute / 60.0)
    
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            cur = r.json().get("current", {})
            return (
                cur.get("temperature_2m", 23.0),
                cur.get("apparent_temperature", 23.0),
                cur.get("relative_humidity_2m", 80.0),
                hora_exacta,
            )
    except Exception:
        pass
    return 23.0, 23.0, 80.0, hora_exacta

def mround(val, base=0.5):
    return round(val / base) * base

def calcular(temp_amb, sens_term, humedad, hora_exacta):
    b7 = 0.45 * temp_amb + 0.55 * sens_term
    b8 = sorted([0.85, 1.5, 1 + 0.025 * (humedad - 80)])[1]
    b9 = 21 + (b7 - 21) * b8
    
    raw_b10 = (
        22.5
        + 3 * math.tanh((b9 - 21) / 7)
        - 0.7 * math.cos(2 * math.pi * (hora_exacta - 15) / 24)
    )
    b10 = sorted([16.0, 30.0, mround(raw_b10, 0.5)])[1]
    
    diff = b9 - b10

    # Lógica de decisiones
    if b9 < 19 and diff < -2:
        modo = "HEAT"
    elif humedad >= 82 and abs(diff) <= 2 and b9 >= 19:
        modo = "DRY"
    elif diff > 1.5:
        modo = "COOL"
    else:
        modo = "AUTO"

    return f"{modo} {b10:g}", round(b7,2), round(b8,3), round(b9,2), b10, diff

st.title("🌡️ Control Térmico del Salón")
st.caption("Matriz de Automatización V2.0 en Python")

temp_amb, sens_term, humedad, hora_exacta = obtener_datos()
config, b7, b8, b9, b10, diff = calcular(temp_amb, sens_term, humedad, hora_exacta)

st.subheader("Configuración Recomendada del Aire")
st.info(f"### ⚙️ **{config}**")

st.markdown("---")
st.subheader("📊 Clima Actual en Lima")

col1, col2 = st.columns(2)
col1.metric("Temperatura Ambiente", f"{temp_amb} °C")
col2.metric("Sensación Térmica", f"{sens_term} °C")

tiempo_actual = obtener_tiempo_lima()
hora_exacta_str = tiempo_actual.strftime("%H:%M:%S")

col3, col4 = st.columns(2)
col3.metric("Humedad Relativa", f"{humedad} %")
col4.metric("Hora Exacta", f"{hora_exacta_str} hrs")

st.markdown("---")
st.caption(f"Última actualización: {hora_exacta_str} (Hora de Lima)")

if st.button("🔄 Actualizar Datos Ahora"):
    st.cache_data.clear()
    st.rerun()
