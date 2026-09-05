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
    "garbage": ["Waste Management", "Environmental Engineering"],
    "waste": ["Waste Management", "Environmental Engineering"],
    "hospital": ["Healthcare", "Health Informatics"],
    "school": ["Education Technology", "Infrastructure"],
    "traffic": ["Transportation", "Traffic Engineering"],
    "flood": ["Hydrology", "GIS", "Disaster Management"]
}

def extract_skills(text):
    lower = text.lower()
    skills = set()
    for keyword, mapped in SKILL_MAP.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", lower):
            skills.update(mapped)
    return sorted(skills)
