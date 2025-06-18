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
def get_city_aqi(city_name):
    lat, lon = get_coordinates(city_name)
    if lat and lon:
        components = get_live_aqi(lat, lon)
        if components:
            aqi_value, category, _ = calculate_aqi(components)
            return aqi_value, category
    return None, "Unavailable"


def get_live_aqi(lat, lon):
    url = f"{BASE_AQI_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
    try:
        response = requests.get(url)
        return response.json()['list'][0]['components']
    except:
        return None

# -------------------------------------------
# ✅ Insert this under "Live Pollutant Values"
# -------------------------------------------

# CPCB pollutant limits (24-hr average)
pollutant_limits = {
    "pm2_5": 60,
    "pm10": 100,
    "so2": 80,
    "no2": 80,
    "o3": 100,
    "co": 2000,
    "nh3": 400
}


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
st.markdown("**Empowering citizens to track air quality and report pollution for a greener tomorrow.** 💚")

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
def get_aqi_advice(aqi_value):
    if aqi_value <= 50:
        return "🟢 Air is Good. Perfect time for a walk or outdoor activities."
    elif aqi_value <= 100:
        return "🟡 Air is Satisfactory. Outdoor activities are safe for most, but sensitive groups may take precautions."
    elif aqi_value <= 200:
        return "🟠 Moderate Air Quality. Consider indoor workouts or wear a mask outdoors."
    elif aqi_value <= 300:
        return "🔴 Poor Air Quality. Limit outdoor activity. Use a purifier indoors if possible."
    elif aqi_value <= 400:
        return "🟣 Very Poor. Avoid outdoor exercise. Use N95 masks and keep windows shut."
    else:
        return "⚫ Severe! Stay indoors with air filtration. Health risk for all groups."

if st.button("🔍 Fetch AQI"):
    # 1. Guard: no input
    if not location:
        st.warning("⚠️ Please enter a location before fetching AQI.")
        st.stop()

    # 2. Geocode
    lat, lon = get_coordinates(location)
    # st.write(f"DEBUG: lat={lat}, lon={lon}")  # optional debug

    # 3. Only proceed if coords valid
    if lat and lon:
        st.success(f"Data for {location}, {selected_date}")
        aqi_data = get_live_aqi(lat, lon)

        # 4. Handle missing API data
        if not aqi_data or not isinstance(aqi_data, dict):
            st.error("❌ Could not fetch AQI data from OpenWeather API.")
        else:
            # 5. Calculate AQI
            aqi_value, aqi_category, aqi_pollutant = calculate_aqi(aqi_data)

            # 6. Display AQI summary
            if aqi_value:
                st.subheader("🌐 Overall AQI Summary")
                st.markdown(
                    f"**AQI Value:** {aqi_value}  \n"
                    f"**Category:** {aqi_category}  \n"
                    f"**Dominant Pollutant:** {aqi_pollutant}"
                )
                st.markdown(f"**🧠 AQI Suggestion:** {get_aqi_advice(aqi_value)}")
                # ✅ Safe check: only run if AQI data is available
                if "aqi_data" in locals() and aqi_data:
                    st.subheader("🌫️ Live Pollutant Values with CPCB Standards")
                    for pollutant, value in aqi_data.items():
                        limit = pollutant_limits.get(pollutant, "N/A")
                        st.write(f"**{pollutant.upper()}**: {value} µg/m³ (CPCB limit: {limit} µg/m³)")
                else:
                    st.warning("AQI data not available right now. Please try again later.")

            # 🔽 NEW: Save daily AQI for trend chart
            aqi_log_file = Path("aqi_trend_log.csv")
            today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

            new_entry = pd.DataFrame([{
               "Date": today_str,
               "Location": location,
               "AQI": aqi_value
}             ])

           if aqi_log_file.exists():
              existing = pd.read_csv(aqi_log_file)
              # Avoid duplicate entries for same day/location
              existing = existing[~((existing["Date"] == today_str) &  (existing["Location"] == location))]   
              updated = pd.concat([existing, new_entry], ignore_index=True)
          else:
              updated = new_entry

          updated.to_csv(aqi_log_file, index=False)

           # 🔽 NEW: Display 7-day AQI trend
           st.subheader("📈 7-Day AQI Trend")

           if aqi_log_file.exists():
              log_df = pd.read_csv(aqi_log_file)
              log_df = log_df[log_df["Location"] == location]
              log_df["Date"] = pd.to_datetime(log_df["Date"])
              log_df = log_df.sort_values("Date").tail(7)

              if not log_df.empty:
                 chart = alt.Chart(log_df).mark_line(point=True).encode(
                      x="Date:T",
                      y="AQI:Q",
                      tooltip=["Date", "AQI"]
                   ).properties(title="AQI Trend (Last 7 Days)")
                   st.altair_chart(chart, use_container_width=True)
               else:
                   st.info("No data yet for trend chart. Please revisit daily.")
               else:
                   st.info("AQI trend data will appear once you visit daily.")

              # 🌍 City-to-City AQI Comparison
              st.subheader("🌍 Compare AQI with Other Cities")

              comparison_cities = ["Delhi", "Pune", "New York", "London"]
              city_comparison_data = []

              for city in comparison_cities:
                  city_aqi, city_cat = get_city_aqi(city)
                  if city_aqi:
                     city_comparison_data.append({"City": city, "AQI": city_aqi, "Category": city_cat})
                  else:
                     city_comparison_data.append({"City": city, "AQI": 0, "Category": "Unavailable"})

             # Add user city at the bottom
             city_comparison_data.append({"City": location, "AQI": aqi_value, "Category": aqi_category})

             df_compare = pd.DataFrame(city_comparison_data)
 
             st.dataframe(df_compare)

             # 📊 Optional: bar chart
             st.subheader("📊 AQI Comparison Chart")
             chart = alt.Chart(df_compare).mark_bar().encode(
                  x="City",
                  y="AQI",
              color="City",
            tooltip=["City", "AQI", "Category"]
).properties(height=300)

            st.altair_chart(chart, use_container_width=True)

                with st.expander("📘 What do AQI values mean? (CPCB Standards)"):
                    st.markdown("""
**Air Quality Index (AQI)** helps us understand how clean or polluted the air is.  
Below are the Indian CPCB-defined categories and their health impacts:

| AQI Range | Category       | Health Impact                                  |
|-----------|----------------|-------------------------------------------------|
| 0–50      | 🟢 Good         | Minimal impact                                  |
| 51–100    | 🟡 Satisfactory  | Minor discomfort for sensitive people           |
| 101–200   | 🟠 Moderate      | Breathing discomfort to sensitive groups        |
| 201–300   | 🔴 Poor          | Discomfort on prolonged exposure                |
| 301–400   | 🟣 Very Poor     | Respiratory issues for most                     |
| 401–500   | ⚫ Severe        | Serious health effects, even on healthy people  |
                    """, unsafe_allow_html=True)
            else:
                st.warning("Unable to determine AQI.")

            # 7. Show pollutant values
            st.subheader("🌫️ Live Pollutant Values")
            for pollutant, value in aqi_data.items():
                st.write(f"**{pollutant.upper()}**: {value} µg/m³")

            # 8. Health tips
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

    else:
        st.error("❌ Could not find location.")

   

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

# -----------------------------------------------------
# ✅ Insert after showing the eco score in scoreboard
# -----------------------------------------------------

with st.expander("🧠 How Your Actions Help (Eco Score Rationale)"):
    st.markdown("""
Here’s how your actions contribute to the environment and your health:

- 🚶 **Walking or Cycling 1 km** → ~200g CO₂ saved (vs. car), improves heart health
- 🛍️ **Using Reusable Bags** → Reduces ~1 kg of plastic per month
- 🌿 **Planting/Caring for a Plant** → Each tree can absorb ~10 kg of CO₂ per year
- 🗑️ **Waste Segregation** → Enables recycling, reduces landfill methane
- 🔌 **Saving Electricity** → Every 1 kWh saved avoids ~0.9 kg CO₂ emissions

These are rough but science-backed estimates — every small act matters! 💪🌍
    """)

# ---------- Pollution Report ----------
st.markdown("### 📢 Report a Pollution Issue")

with st.form("pollution_form"):
    rep_name     = st.text_input("Your Name", key="rep_name")
    rep_email    = st.text_input("Email", key="rep_email")
    rep_location = st.text_input("Location")
    issue_type   = st.selectbox("Pollution Type", ["Air", "Noise", "Water", "Solid Waste", "Other"])
    issue_desc   = st.text_area("Describe the issue in detail")

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
# --------------------------------------------
# ✅ Insert after pollution report submission
# --------------------------------------------

st.success("📩 Thank you! Your report has been submitted.")

st.markdown("""
---
📢 **Disclaimer**  
We value your privacy. Your name, email, and reports are stored securely and used only for environmental awareness and action.  
Data is **not shared** with anyone without your permission.  
Reports may be used in **anonymized form** to raise concerns with local authorities, NGOs, or media.

Together, we can make our environment better. 💚
""")


# Admin access to download pollution reports
admin_key_input = st.text_input("Enter admin key to access report data", type="password")

if admin_key_input == st.secrets["ADMIN_KEY"]:
    st.success("✅ Admin access granted.")
    
    # Load and preview the CSV
    issue_file = Path("pollution_reports.csv")
    if issue_file.exists():
        report_df = pd.read_csv(issue_file)
        st.dataframe(report_df)

        # Download button
        csv = report_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Pollution Report CSV", data=csv, file_name='pollution_reports.csv', mime='text/csv')
    else:
        st.warning("📭 No reports found yet.")

