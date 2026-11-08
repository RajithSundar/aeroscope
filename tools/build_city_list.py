"""
tools/build_city_list.py
Builds config/ncap_cities.csv: the 131 cities on CPCB's official NCAP list
("List of 131 Non-Attainment cities", https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf),
geocoded with the Open-Meteo geocoding API (no key needed).

Small industrial towns that geocoders tend to mis-place are pinned by hand in OVERRIDES.
Re-run only when the official list changes:  python tools/build_city_list.py
"""

import csv
import os
import re
import sys
import time

import requests

SOURCE_URL = "https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf"

# (state, city as written by CPCB). Cities marked * in the source are "million-plus cities
# but not part of non-attainment cities" (funded under the 15th Finance Commission).
NCAP_LIST = {
    "Andhra Pradesh": ["Guntur", "Kurnool", "Nellore", "Vijayawada", "Vishakhapatnam", "Anantapur",
                       "Chitoor", "Eluru", "Kadapa", "Ongole", "Rajahmundry", "Srikakulam", "Vizianagaram"],
    "Assam": ["Guwahati", "Nagaon", "Nalbari", "Sibsagar", "Silchar"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur"],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": ["Bhilai", "Korba", "Raipur"],
    "Delhi": ["Delhi"],
    "Gujarat": ["Surat", "Ahmedabad", "Vadodara", "Rajkot*"],
    "Himachal Pradesh": ["Baddi", "Damtal", "Kala Amb", "Nalagarh", "Paonta Sahib", "Parwanoo", "Sunder Nagar"],
    "Jammu & Kashmir": ["Jammu", "Srinagar"],
    "Jharkhand": ["Dhanbad", "Jamshedpur*", "Ranchi*"],
    "Karnataka": ["Bangalore", "Devanagere", "Gulburga", "Hubli-Dharwad"],
    "Madhya Pradesh": ["Bhopal", "Dewas", "Indore", "Sagar", "Ujjain", "Gwalior", "Jabalpur*"],
    "Maharashtra": ["Akola", "Amravati", "Aurangabad", "Badlapur", "Chandrapur", "Jalgaon", "Jalna", "Kolhapur",
                    "Latur", "Mumbai", "Nagpur", "Nashik", "Navi Mumbai", "Pune", "Sangli", "Solapur",
                    "Ulhasnagar", "Thane", "Vasai-Virar*"],
    "Meghalaya": ["Byrnihat"],
    "Nagaland": ["Dimapur", "Kohima"],
    "Odisha": ["Angul", "Balasore", "Bhubaneswar", "Cuttack", "Rourkela", "Talcher", "Kalinga Nagar"],
    "Punjab": ["Dera Bassi", "Gobindgarh", "Jalandhar", "Khanna", "Ludhiana", "Naya Nangal",
               "Pathankot/Dera Baba", "Patiala", "Amritsar"],
    "Rajasthan": ["Alwar", "Jaipur", "Jodhpur", "Kota", "Udaipur"],
    "Tamil Nadu": ["Thoothukudi", "Trichy", "Madurai", "Chennai*"],
    "Telangana": ["Hyderabad", "Nalgonda", "Patancheruvu", "Sangareddy"],
    "Uttar Pradesh": ["Agra", "Allahabad", "Anpara", "Bareily", "Firozabad", "Gajraula", "Ghaziabad", "Jhansi",
                      "Kanpur", "Khurja", "Lucknow", "Moradabad", "Noida", "Raebareli", "Varanasi",
                      "Gorakhpur", "Meerut*"],
    "Uttarakhand": ["Kashipur", "Rishikesh", "Dehradun"],
    "West Bengal": ["Kolkata", "Asansol & Raniganj", "Barrackpore", "Durgapur", "Haldia", "Howrah"],
    "Haryana": ["Faridabad*"],
}

# Hand-checked coordinates (city centre / main industrial area) for names geocoders get wrong.
OVERRIDES = {
    "Damtal": (32.2600, 75.6800),
    "Kala Amb": (30.5050, 77.2060),
    "Baddi": (30.9578, 76.7914),
    "Nalagarh": (31.0417, 76.7230),
    "Parwanoo": (30.8372, 76.9614),
    "Sunder Nagar": (31.5332, 76.8923),
    "Paonta Sahib": (30.4381, 77.6245),
    "Byrnihat": (26.0450, 91.8710),
    "Kalinga Nagar": (20.9460, 86.0210),
    "Gobindgarh": (30.6700, 76.3000),          # Mandi Gobindgarh
    "Naya Nangal": (31.3850, 76.3750),         # Nangal
    "Pathankot/Dera Baba": (32.2643, 75.6421),  # Pathankot
    "Dera Bassi": (30.5873, 76.8436),
    "Patancheruvu": (17.5333, 78.2645),
    "Anpara": (24.2003, 82.7889),
    "Gajraula": (28.8460, 78.2380),
    "Badlapur": (19.1550, 73.2650),
    "Asansol & Raniganj": (23.6739, 86.9524),  # Asansol (Raniganj is ~15 km west)
    "Barrackpore": (22.7642, 88.3776),
    "Hubli-Dharwad": (15.3647, 75.1240),
    "Vasai-Virar": (19.3919, 72.8397),
    "Navi Mumbai": (19.0330, 73.0297),
    "Delhi": (28.6139, 77.2090),
    "Khanna": (30.7050, 76.2220),
    "Sangareddy": (17.6240, 78.0870),
    "Nalgonda": (17.0575, 79.2684),
    "Sagar": (23.8388, 78.7378),
    "Aurangabad": (19.8762, 75.3433),          # Chhatrapati Sambhajinagar, Maharashtra
    "Raebareli": (26.2309, 81.2330),
    "Rishikesh": (30.0869, 78.2676),
    "Kashipur": (29.2104, 78.9619),
    "Sibsagar": (26.9826, 94.6425),
    "Devanagere": (14.4644, 75.9218),
}

# Display names (common modern spelling); CPCB's spelling is kept in `cpcb_name`.
DISPLAY = {
    "Vishakhapatnam": "Visakhapatnam", "Chitoor": "Chittoor", "Sibsagar": "Sivasagar",
    "Bangalore": "Bengaluru", "Devanagere": "Davanagere", "Gulburga": "Kalaburagi",
    "Trichy": "Tiruchirappalli", "Allahabad": "Prayagraj", "Bareily": "Bareilly",
    "Gobindgarh": "Mandi Gobindgarh", "Naya Nangal": "Nangal", "Pathankot/Dera Baba": "Pathankot",
    "Asansol & Raniganj": "Asansol-Raniganj", "Aurangabad": "Chhatrapati Sambhajinagar (Aurangabad)",
}

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
STATE_ALIASES = {"Jammu & Kashmir": "Jammu and Kashmir", "Delhi": "National Capital Territory of Delhi"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def geocode(name: str, state: str):
    query = DISPLAY.get(name, name).split(" (")[0]
    resp = requests.get(GEOCODE_URL, params={"name": query, "count": 20, "country": "IN", "language": "en"}, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    want = STATE_ALIASES.get(state, state).lower()
    in_state = [r for r in results if (r.get("admin1") or "").lower() == want]
    pool = in_state or results
    if not pool:
        return None
    best = max(pool, key=lambda r: r.get("population") or 0)
    return best["latitude"], best["longitude"], bool(in_state)


def main():
    out_path = os.path.join("config", "ncap_cities.csv")
    os.makedirs("config", exist_ok=True)
    rows, warnings = [], []
    for state, cities in NCAP_LIST.items():
        for raw in cities:
            million_plus_only = raw.endswith("*")
            name = raw.rstrip("*")
            if name in OVERRIDES:
                lat, lon = OVERRIDES[name]
                method = "manual"
            else:
                hit = geocode(name, state)
                time.sleep(0.15)
                if hit is None:
                    warnings.append(f"NOT FOUND: {name}, {state}")
                    continue
                lat, lon, state_ok = hit
                method = "open-meteo-geocoding"
                if not state_ok:
                    warnings.append(f"State mismatch, check by hand: {name}, {state} -> {lat:.3f},{lon:.3f}")
            display = DISPLAY.get(name, name)
            rows.append({
                "city_id": slugify(display.split(" (")[0]),
                "city": display,
                "cpcb_name": name,
                "state": state,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "list_status": "million_plus_fc15" if million_plus_only else "non_attainment",
                "coord_source": method,
            })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        f.write(f"# Source: {SOURCE_URL} (CPCB 'List of 131 Non-Attainment cities'). Built {time.strftime('%Y-%m-%d')}.\n")
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} cities to {out_path}")
    for w in warnings:
        print("  !", w)
    if len(rows) != 131:
        print(f"  ! Expected 131 cities, got {len(rows)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
