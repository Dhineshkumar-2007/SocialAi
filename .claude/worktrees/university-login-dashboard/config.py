import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///societal_ai.db")
    AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    BGE_MODEL = os.getenv("BGE_MODEL", "BAAI/bge-small-en-v1.5")
    CLASSIFIER_MODEL = os.getenv(
        "CLASSIFIER_MODEL",
        "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
    )
    VISION_MODEL = os.getenv(
        "VISION_MODEL",
        "Salesforce/blip-image-captioning-base"
    )
    DUPLICATE_THRESHOLD = float(os.getenv("DUPLICATE_THRESHOLD", "0.82"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    UNIVERSITY_RESPONSE_TIMEOUT_HOURS = int(os.getenv("UNIVERSITY_RESPONSE_TIMEOUT_HOURS", "72"))
    MAX_ASSIGNMENT_ROUNDS = int(os.getenv("MAX_ASSIGNMENT_ROUNDS", "3"))
