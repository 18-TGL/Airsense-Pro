import streamlit as st
import pandas as pd
from datetime import date
import requests
import altair as alt
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

# ---------- API Setup ----------
API_KEY = st.secrets["API_KEY"]
BASE_AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# ---------- AQI Calculation ----------
def calculate_aqi(pollutants):
    breakpoints = {
        "pm2_5": [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), (91, 120, 201, 300), (121, 250, 301, 400), (251, 350, 401, 500)],
        "pm10": [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200), (251, 350, 201, 300), (351, 430, 301, 400), (431, 500, 401, 500)],
        "so2": [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200), (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 2000, 401, 500)],
        "no2": [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200), (181, 280, 201, 300), (281, 400, 301, 400), (401, 500, 401, 500)],
        "o3": [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200), (169, 208, 201, 300), (209, 748, 301, 400), (749, 1000, 401, 500)]
    }
    category_map = [(0, 50, "🟢 Good"), (51, 100, "🟡 Satisfactory"), (101, 200, "🟠 Moderate"), (201, 300, "🔴 Poor"), (301, 400, "🟣 Very Poor"), (401, 500, "⚫ Severe")]
    def get_individual_aqi(concentration, ranges):
        for (c_low, c_high, aqi_low, aqi_high) in ranges:
            if c_low <= concentration <= c_high:
                return round(((aqi_high - aqi_low) / (c_high - c_low)) * (concentration - c_low) + aqi_low)
        return None
    results = {}
    for pollutant, value in pollutants.items():
        if pollutant in breakpoints:
            aqi = get_individual_aqi(value, breakpoints[pollutant])
            if aqi is not None:
                results[pollutant] = aqi
    if results:
        max_pollutant = max(results, key=results.get)
        max_aqi = results[max_pollutant]
        for (low, high, category) in category_map:
            if low <= max_aqi <= high:
                return max_aqi, category, max_pollutant.upper()
    return None, "Unavailable", ""

def get_coordinates(location_name):
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": location_name, "limit": 1, "appid": API_KEY}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
        else:
            st.error("❌ No location found. Please check your input.")
    except Exception as e:
        st.error(f"Error fetching coordinates: {e}")
    return None, None

def get_live_aqi(lat, lon):
    url = f"{BASE_AQI_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
    try:
        response = requests.get(url)
        return response.json()['list'][0]['components']
    except:
        return None

def get_recommendation(pm25, pm10, o3, nox, so2, co):
    tips = []
    if pm25 > 60: tips.append("😷 PM2.5 is high – Avoid outdoor activity and use an N95 mask.")
    if pm10 > 100: tips.append("🚫 PM10 exceeds safe limits – Avoid dusty areas and construction zones.")
    if o3 > 100: tips.append("🌞 Ozone is high – Stay indoors during afternoon hours.")
    if nox > 80: tips.append("🚦 NOx is elevated – Avoid high-traffic areas.")
    if so2 > 80: tips.append("🧪 SO₂ is high – People with asthma should stay indoors.")
    if co > 2000: tips.append("☠️ CO is high – Avoid enclosed or poorly ventilated areas.")
    if not tips: tips.append("✅ All pollutant levels are within safe limits. Enjoy your day!")
    return tips

# ---------- Streamlit UI ----------
st.set_page_config(page_title="AirSense Pro", page_icon="🌿")
st.title("🌿 AirSense Pro")
st.markdown("##### 🌍 A Smart Air Quality Prediction Tool for Everyone")

st.markdown("""
    <style>
    body { background-color: white; font-family: 'Segoe UI', sans-serif; }
    h1 { color: #2e7d32; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

aqi_data = None
mode = st.selectbox("Select Mode", ["Citizen", "Industry (Coming Soon)"])

if mode == "Citizen":
    st.subheader("📍 Enter Your Location")
    location = st.text_input("Enter city or area", placeholder="e.g., Mumbai")
    selected_date = st.date_input("Select date", value=date.today())

    if st.button("🔍 Fetch AQI"):
       if not location:
        st.warning("⚠️ Please enter a location before fetching AQI.")
        st.stop()

        lat, lon = get_coordinates(location)
        st.write("DEBUG: lat =", lat, ", lon =", lon)

    if lat and lon:
       st.success(f"Data for {location}, {selected_date}")
       aqi_data = get_live_aqi(lat, lon)

    if not aqi_data or not isinstance(aqi_data, dict):
        st.error("❌ Could not fetch AQI data from OpenWeather API.")
    else:
        aqi_value, aqi_category, aqi_pollutant = calculate_aqi(aqi_data)

        if aqi_value:
            st.subheader("🌐 Overall AQI Summary")
            st.markdown(f"**AQI Value:** {aqi_value}  \n**Category:** {aqi_category}  \n**Dominant Pollutant:** {aqi_pollutant}")

            with st.expander("📘 What do AQI values mean? (CPCB Standards)"):
                st.markdown("""
**Air Quality Index (AQI)** helps us understand how clean or polluted the air is.  
Below are the Indian CPCB-defined categories and their health impacts:

| AQI Range | Category      | Color Code | Health Impact |
|-----------|---------------|------------|----------------|
| 0–50      | 🟢 Good        | Green      | Minimal impact |
| 51–100    | 🟡 Satisfactory | Yellow    | Minor discomfort for sensitive people |
| 101–200   | 🟠 Moderate     | Orange    | Breathing discomfort to sensitive groups |
| 201–300   | 🔴 Poor         | Red       | Discomfort on prolonged exposure |
| 301–400   | 🟣 Very Poor    | Purple    | Respiratory issues for most |
| 401–500   | ⚫ Severe       | Dark Gray | Serious health effects, even on healthy people |
                """, unsafe_allow_html=True)
        else:
            st.warning("Unable to determine AQI.")

        st.subheader("🌫️ Live Pollutant Values")
        for pollutant, value in aqi_data.items():
            st.write(f"**{pollutant.upper()}**: {value} µg/m³")

        nox = aqi_data.get("no", 0) + aqi_data.get("no2", 0)
        st.subheader("💡 Health Recommendations")
        for tip in get_recommendation(
            pm25=aqi_data.get("pm2_5", 0),
            pm10=aqi_data.get("pm10", 0),
            o3=aqi_data.get("o3", 0),
            nox=nox,
            so2=aqi_data.get("so2", 0),
            co=aqi_data.get("co", 0)
        ):
            st.markdown(f"- {tip}")


# ---------- Eco Scoreboard ----------
st.markdown("---")
st.markdown("## 🌱 Eco Scoreboard & 📝 Pollution Reporting")

with st.form("eco_score_form"):
    st.markdown("### ✅ Eco Scoreboard (Your Green Contribution Today)")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    city = st.text_input("City / Area")

    st.markdown("Select eco-friendly actions you performed today:")
    eco_actions = {
        "🚶 Walked or Cycled": st.checkbox("Walked or Cycled instead of using a vehicle"),
        "🛍️ Reusable Bag": st.checkbox("Used cloth or reusable bags"),
        "🌿 Tree or Plant Care": st.checkbox("Planted or cared for plants"),
        "🗑️ Waste Segregation": st.checkbox("Segregated dry and wet waste"),
        "🔌 Saved Electricity": st.checkbox("Turned off lights/fans when not needed")
    }

    submitted_eco = st.form_submit_button("🎯 Submit Eco Score")

    if submitted_eco:
        score = sum(eco_actions.values()) * 20
        st.success(f"🎯 Your Eco Score: {score}/100")
        st.balloons()
        entry = pd.DataFrame([{
            "Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Name": name,
            "Email": email,
            "City": city,
            "Score": score
        }])
        eco_file = Path("eco_scores.csv")
        if eco_file.exists():
            existing = pd.read_csv(eco_file)
            updated = pd.concat([existing, entry], ignore_index=True)
        else:
            updated = entry
        updated.to_csv(eco_file, index=False)

# ---------- Pollution Report ----------
st.markdown("### 📢 Report a Pollution Issue")

with st.form("pollution_form"):
    rep_name = st.text_input("Your Name", key="rep_name")
    rep_email = st.text_input("Email", key="rep_email")
    rep_location = st.text_input("Location")
    issue_type = st.selectbox("Pollution Type", ["Air", "Noise", "Water", "Solid Waste", "Other"])
    issue_desc = st.text_area("Describe the issue in detail")

    submitted_issue = st.form_submit_button("🚨 Submit Report")

    if submitted_issue:
        report = pd.DataFrame([{
            "Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Name": rep_name,
            "Email": rep_email,
            "Location": rep_location,
            "Type": issue_type,
            "Description": issue_desc
        }])
        issue_file = Path("pollution_reports.csv")
        if issue_file.exists():
            existing = pd.read_csv(issue_file)
            updated = pd.concat([existing, report], ignore_index=True)
        else:
            updated = report
        updated.to_csv(issue_file, index=False)
        st.success("📩 Thank you! Your report has been submitted.")
