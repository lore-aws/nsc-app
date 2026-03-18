import streamlit as st
import requests
from datetime import datetime

API_KEY = st.secrets["OPENWEATHER_API_KEY"]

# -------------------------
# FUNCTIES
# -------------------------

def geocode(location):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={API_KEY}"
    res = requests.get(url).json()
    if not res:
        return None
    return res[0]["lat"], res[0]["lon"], res[0]["name"]

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return requests.get(url).json()

def get_forecast(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return requests.get(url).json()

def nsc_risk(cloud_cover, night_temp, hour):
    score = 0
    sun_factor = 1 - (cloud_cover / 100)

    if sun_factor > 0.7:
        score += 2
    elif sun_factor > 0.4:
        score += 1

    if night_temp < 5:
        score += 2
    elif night_temp < 10:
        score += 1
    else:
        score -= 1

    if 12 <= hour <= 18:
        score += 2
    elif 8 <= hour < 12:
        score += 1
    elif 0 <= hour < 6:
        score -= 1

    if score <= 1:
        return "Laag risico", "green"
    elif score <= 3:
        return "Risico", "orange"
    else:
        return "Hoog risico", "red"

# -------------------------
# UI
# -------------------------

st.set_page_config(page_title="NSC Gras Monitor", page_icon="🌱")
st.title("🌱 NSC Risico in Gras")

location = st.text_input("Geef een locatie in (bv. Brussel)", placeholder="Utrecht, NL")

if location:
    geo = geocode(location)

    if geo is None:
        st.error("Locatie niet gevonden")
    else:
        lat, lon, name = geo
        
        # --- HUIDIG WEER ---
        data = get_weather(lat, lon)
        
        if data.get("cod") != 200:
            st.error("Kon weergegevens niet ophalen.")
        else:
            st.header(f"Actueel: {name}")
            cloud = data["clouds"]["all"]
            temp = data["main"]["temp"]
            # We gebruiken de huidige temp even als 'nacht_temp' indicator voor de simpele berekening
            # Of je kunt de min_temp van de dag gebruiken
            night_temp = data["main"]["temp_min"] 
            hour = datetime.now().hour

            risk, color = nsc_risk(cloud, night_temp, hour)

            # Visuele weergave van huidig risico
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Temperatuur", f"{temp}°C")
                st.metric("Bewolking", f"{cloud}%")
            
            with col2:
                if color == "green":
                    st.success(f"**{risk}**\n\nVeilig om te grazen.")
                elif color == "orange":
                    st.warning(f"**{risk}**\n\nLet op met gevoelige paarden.")
                else:
                    st.error(f"**{risk}**\n\nBeter nu niet grazen.")

            # --- VOORSPELLING VOOR KOMENDE UREN ---
            st.divider()
            st.subheader("📅 Voorspelling komende 24 uur")
            
            forecast_data = get_forecast(lat, lon)
            
            if forecast_data.get("cod") == "200":
                # We pakken de eerste 8 datapunten (8 x 3 uur = 24 uur)
                for item in forecast_data["list"][:8]:
                    dt = datetime.fromtimestamp(item["dt"])
                    f_hour = dt.hour
                    f_temp = item["main"]["temp"]
                    f_cloud = item["clouds"]["all"]
                    
                    # Bereken risico voor dat tijdstip
                    f_risk, f_color = nsc_risk(f_cloud, night_temp, f_hour)
                    
                    # Kleur-emoji voor de lijst
                    emoji = "🟢" if f_color == "green" else "🟡" if f_color == "orange" else "🔴"
                    
                    st.write(f"{dt.strftime('%H:%M')} | {emoji} **{f_risk}** | Temp: {f_temp:.1f}°C | Wolken: {f_cloud}%")
            else:
                st.info("Voorspelling kon niet worden geladen.")