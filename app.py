import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = st.secrets["OPENWEATHER_API_KEY"]

# -------------------------
# FUNCTIES
# -------------------------

def geocode(location):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={API_KEY}"
    res = requests.get(url).json()
    return (res[0]["lat"], res[0]["lon"], res[0]["name"]) if res else None

def get_weather_data(lat, lon):
    # We halen de 5-daagse voorspelling op (bevat alle data die we nodig hebben)
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return requests.get(url).json()

def get_night_min(forecast_list, target_date):
    """Zoekt de minimumtemperatuur van de nacht voorafgaand aan de target_date."""
    night_temps = []
    for item in forecast_list:
        dt = datetime.fromtimestamp(item["dt"])
        # We kijken naar temperaturen tussen 00:00 en 07:00 van de betreffende dag
        if dt.date() == target_date.date() and 0 <= dt.hour <= 6:
            night_temps.append(item["main"]["temp_min"])
    
    return min(night_temps) if night_temps else 7  # 7 is een veilige aanname als data ontbreekt

def nsc_risk(cloud_cover, night_temp, hour, humidity, temp_current):
    score = 0
    sun_factor = 1 - (cloud_cover / 100)

    # 1. ZONLICHT & TEMP (Productie)
    # Veel zon bij een gematigde temperatuur (10-25°C) geeft maximale assimilatie
    if sun_factor > 0.7:
        score += 3
    elif sun_factor > 0.4:
        score += 1

    # 2. NACHTTEMPERATUUR (Verbruik)
    if night_temp <= 0:
        score += 4  # Extreem risico: suikers "bevroren" in het blad
    elif night_temp < 5:
        score += 2
    elif night_temp > 12:
        score -= 2  # Warme nacht = veel verbruik = veiliger gras

    # 3. WATERSTRESS (Indicator via luchtvochtigheid)
    # Lage luchtvochtigheid + hoge temp = groeistop = suikerophoping
    if humidity < 40 and temp_current > 20:
        score += 2

    # 4. TIJDSTIP (Cumulatief effect)
    if 14 <= hour <= 19:
        score += 2  # Piek aan het einde van de middag
    elif 4 <= hour <= 8:
        score -= 2  # Veiligste moment: vlak na zonsopgang

    # Risico bepaling (schaal is nu ruimer door extra factoren)
    if score <= 4: return "Laag risico", "green"
    elif score <= 7: return "Matig risico", "orange"
    else: return "Hoog risico", "red"

# -------------------------
# UI
# -------------------------

st.set_page_config(page_title="NSC Gras Monitor", page_icon="🌱")
st.title("🌱 NSC Risico Monitor")
st.caption("Schatting van suikergehalte in gras op basis van weerdata.")

location = st.text_input("Locatie", placeholder="Bv. Brussel")

if location:
    geo = geocode(location)
    if not geo:
        st.error("Locatie niet gevonden.")
    else:
        lat, lon, name = geo
        data = get_weather_data(lat, lon)

        if data.get("cod") == "200":
            forecast_list = data["list"]
            current = forecast_list[0]
            
            # --- HUIDIG ---
            st.subheader(f"Actueel in {name}")
            curr_dt = datetime.fromtimestamp(current["dt"])
            curr_night_min = get_night_min(forecast_list, curr_dt)
            risk, color = nsc_risk(current["clouds"]["all"], curr_night_min, curr_dt.hour, current["main"]["humidity"], current["main"]["temp"])

            # Belangrijkste huidige stats in kolommen
            col1, col2, col3, col4 = st.columns([0.85, 1.15, 0.85, 1.15])
            col1.metric("Temperatuur", f"{current['main']['temp']:.1f}°C")
            col2.metric("Minimum afgelopen nacht", f"{curr_night_min:.1f}°C")
            col3.metric("Bewolking", f"{current['clouds']['all']}%")
            col4.metric("Risiconiveau", f"{risk}")
            
            # --- TABEL VOORSPELLING ---
            st.divider()
            st.subheader("Voorspelling komende 24 uur")

            table_data = []
            for item in forecast_list[:9]:
                dt = datetime.fromtimestamp(item["dt"])
                night_min = get_night_min(forecast_list, dt)
                
                f_risk, f_color = nsc_risk(
                    item["clouds"]["all"], 
                    night_min, 
                    dt.hour, 
                    item["main"]["humidity"], 
                    item["main"]["temp"]
                )
                
                emoji = "🟢" if f_color == "green" else "🟡" if f_color == "orange" else "🔴"
                
                table_data.append({
                    "Tijdstip": dt.strftime('%Hu%M'),
                    "NSC Risico": f"{emoji} {f_risk}",
                    "Temperatuur": f"{item['main']['temp']:.1f}°C",
                    "Wolken": f"{item['clouds']['all']}%"
                })

            # Zet de lijst om naar een DataFrame
            df = pd.DataFrame(table_data)

            # Toon de tabel zonder rijnummers
            st.dataframe(df, hide_index = True)
            st.divider()
            st.info("Deze voorspelling is een indicatie op basis van de huidige weersomstandigheden en is geen garantie.\nObserveer je paarden goed en schat in of ze kunnen grazen.")
        else:
            st.error("Kon geen weerdata ophalen.")