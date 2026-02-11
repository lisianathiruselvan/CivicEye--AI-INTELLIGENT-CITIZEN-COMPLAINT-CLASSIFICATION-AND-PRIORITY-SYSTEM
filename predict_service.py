import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

# ---------------- LOAD ----------------
category_model = pickle.load(open("best_category_model.pkl", "rb"))
label_encoder = pickle.load(open("label_encoder.pkl", "rb"))
sbert = SentenceTransformer("all-MiniLM-L6-v2")

# Ensure multi_class exists (fix for older models)
if not hasattr(category_model, "multi_class"):
    category_model.multi_class = 'ovr'  # one-vs-rest

CIVIC_WORDS = ["street", "road", "water", "gas", "fire", "parking",
    "noise", "traffic", "sanitation", "sewer", "animal",
    "building", "electric", "garbage", "pothole"]

HIGH = ["fire", "flames", "burning", "smoke", "explosion", "blast","gas", "gas leak", "gas smell", "leakage", "pipeline leak","chemical spill", "toxic", "fumes", "hazardous","electric", "live wire", "electric shock", "short circuit",
    "sparks", "power line down", "fallen wire", "exposed wire",
    "transformer burst", "high voltage","water leak", "main burst", "water main break", "flood",
    "flooding", "sewage", "sewer overflow", "drain overflow",
    "manhole overflow","fight", "violence", "weapon", "knife", "gun"]
MEDIUM = ["street", "sanitation", "traffic", "road", "pothole", "garbage", "noise"]

# ---------------- PRIORITY FROM CATEGORY ----------------
def get_priority_from_category(category):
    category = category.lower()
    if any(w in category for w in HIGH):
        return "High"
    elif any(w in category for w in MEDIUM):
        return "Medium"
    else:
        return "Low"

# ---------------- MAIN PREDICT FUNCTION ----------------
def predict_complaint(text):

    text_lower = text.lower()

    # 🚫 Too short
    if len(text.split()) <= 2:
        return {"category": "Too little information", "priority": "Medium"}

    # 🚫 Not civic domain
    if not any(word in text_lower for word in CIVIC_WORDS):
        return {"category": "Not a civic complaint", "priority": "Low"}

    # 🚨 Safety overrides BEFORE model
    if any(w in text_lower for w in ["gas leak", "live wire", "electric shock", "fire", "flood","gas","pipeline","dead body", "unconscious person", "injured person",
    "bleeding", "medical emergency","radiation", "bomb threat", "suspicious package", "accident", "crash", "collision", "vehicle overturned",
    "blocked highway", "oil spill on road","open manhole", "deep pothole", "road cave-in",
    "landslide", "tree fallen", "tree about to fall","building collapse", "wall collapse", "ceiling collapse",
    "bridge crack", "road collapse", "sinkhole",
    "crack in building", "falling debris","electric wire"]):
        return {"category": "Emergency Utility Issue", "priority": "High"}

    # 🔮 SBERT embedding
    embedding = sbert.encode([text])
    embedding = np.array(embedding).astype(np.float32)

    # 5️⃣ Model prediction
    try:
        probs = category_model.predict_proba(embedding)[0]
        best_idx = np.argmax(probs)
        category = label_encoder.classes_[best_idx]
        confidence = float(probs[best_idx])
    except AttributeError:
        # fallback if predict_proba fails
        category = category_model.predict(embedding)[0]
        confidence = 1.0  # assume high confidence

    # ❌ Low confidence rejection
    if confidence < 0.60:
        return {"category": "Needs manual review", "priority": "Medium"}

    priority = get_priority_from_category(category)

    return {
        "category": category,
        "priority": priority,
    }
