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

    if len(res) == 0:
        return None
    
    return res[0]["lat"], res[0]["lon"], res[0]["name"]

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return requests.get(url).json()

def get_night_temp(lat, lon):
    # haal huidige weerdata
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    res = requests.get(url).json()

    # fallback: gebruik huidige temp als nachttemp
    night_temp = res.get("main", {}).get("temp", None)
    if night_temp is None:
        night_temp = 5  # default veilige waarde
    return night_temp

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

st.title("🌱 NSC Risico in Gras")

location = st.text_input("Geef een locatie in (bv. Brussel)")

if location:
    geo = geocode(location)

    if geo is None:
        st.error("Locatie niet gevonden")
    else:
        lat, lon, name = geo
        data = get_weather(lat, lon)

    if data.get("cod") != 200:
        st.error("Locatie niet gevonden")
    else:
        st.subheader(f"Gegevens voor {name}")
        cloud = data["clouds"]["all"]
        temp = data["main"]["temp"]
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]

        night_temp = get_night_temp(lat, lon)
        hour = datetime.now().hour

        risk, color = nsc_risk(cloud, night_temp, hour)

        st.subheader(f"Resultaat: {risk}")

        if color == "green":
            st.success("Laag risico om te grazen")
        elif color == "orange":
            st.warning("Let op met grazen")
        else:
            st.error("Hoog risico – beter vermijden")

        st.write("### Details")
        st.write(f"Temperatuur: {temp}°C")
        #st.write(f"Nacht minimum: {night_temp:.1f}°C")
        st.write(f"Bewolking: {cloud}%")