import re

SKILL_MAP = {
    "water": ["Water Quality Analysis", "Hydrology", "Environmental Engineering"],
    "borewell": ["Hydrology", "Water Quality Analysis"],
    "groundwater": ["Hydrology", "GIS", "Water Quality Analysis"],
    "sensor": ["IoT", "Sensor Networks", "Embedded Systems"],
    "iot": ["IoT", "Sensor Networks", "Embedded Systems"],
    "machine learning": ["Machine Learning", "Data Science"],
    "ai": ["Artificial Intelligence", "Machine Learning"],
    "gis": ["GIS", "Geospatial Analysis"],
    "satellite": ["Remote Sensing", "GIS"],
    "crop": ["Agricultural Engineering", "Remote Sensing"],
    "farm": ["Agriculture", "Agricultural Engineering", "IoT"],
    "road": ["Civil Engineering", "Infrastructure"],
    "bridge": ["Civil Engineering", "Structural Engineering"],
    "structural": ["Structural Engineering", "Civil Engineering"],
    "building": ["Civil Engineering", "Structural Engineering", "Architecture"],
    "construction": ["Civil Engineering", "Infrastructure"],
    "garbage": ["Waste Management", "Environmental Engineering"],
    "waste": ["Waste Management", "Environmental Engineering"],
    "hospital": ["Healthcare", "Health Informatics"],
    "school": ["Education Technology", "Infrastructure"],
    "traffic": ["Transportation", "Traffic Engineering"],
    "transport": ["Transportation", "Infrastructure"],
    "junction": ["Traffic Engineering", "Civil Engineering"],
    "signal": ["Traffic Engineering", "IoT"],
    "accident": ["Public Safety", "Transportation"],
    "flood": ["Hydrology", "GIS", "Disaster Management"],
    # Expanded keywords for better coverage
    "drinking": ["Water Quality Analysis", "Hydrology"],
    "contamination": ["Water Quality Analysis", "Environmental Engineering"],
    "pollution": ["Environmental Engineering", "Waste Management"],
    "sewage": ["Waste Management", "Environmental Engineering"],
    "irrigation": ["Agricultural Engineering", "Hydrology"],
    "electricity": ["Energy", "Civil Engineering"],
    "power": ["Energy", "Civil Engineering"],
    "blackout": ["Energy", "Civil Engineering"],
    "climate": ["Environmental Engineering", "Climate Analytics"],
    "carbon": ["Environmental Engineering", "Climate Analytics"],
    "renewable": ["Energy", "Environmental Engineering"],
    "solar": ["Energy", "Environmental Engineering"],
    "disaster": ["Disaster Management", "Civil Engineering"],
    "emergency": ["Healthcare", "Disaster Management"],
    "dog": ["Healthcare", "Veterinary Medicine", "Public Health"],
    "stray": ["Healthcare", "Veterinary Medicine", "Public Health"],
    "bite": ["Healthcare", "Emergency Medicine"],
    "animal": ["Veterinary Medicine", "Public Health"],
    "employment": ["Education Technology", "Vocational Training"],
    "unemployment": ["Education Technology", "Social Engineering"],
    "vocational": ["Education Technology", "Vocational Training"],
    "training": ["Education Technology", "Vocational Training"],
    "youth": ["Education Technology", "Social Engineering"],
    "community": ["Social Engineering", "Infrastructure"],
}

def extract_skills(text):
    lower = text.lower()
    skills = set()
    for keyword, mapped in SKILL_MAP.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
            skills.update(mapped)
    return sorted(skills)
