# =========================================
# CivicEye - Member 2 ML Models (FINAL)
# Handles Rare Classes + SMOTE + Encoding
# =========================================

import pickle
import pandas as pd
import numpy as np
import time
from collections import Counter
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

# -----------------------------------------
# LOAD SBERT EMBEDDINGS
# -----------------------------------------
print("\n📥 Loading SBERT embeddings...")

with open(r"C:\Users\SEC\Downloads\CivicEyeSBERT\CivicEye\data\processed\Sbert_embeddings.pkl", "rb") as f:
    data = pickle.load(f)

X = np.array(data["embeddings"])
y = np.array(data["labels"])

print("✅ Embeddings loaded!")
print("📊 Original class distribution:", Counter(y))

# -----------------------------------------
# HANDLE RARE CLASSES + SAFE SMOTE
# -----------------------------------------
print("\n🔍 Checking class counts before SMOTE...")
class_counts = Counter(y)

# Remove classes with only 1 sample
valid_indices = [i for i, label in enumerate(y) if class_counts[label] > 1]
X_filtered = X[valid_indices]
y_filtered = y[valid_indices]

print("Classes eligible for SMOTE:", Counter(y_filtered))

# Safe neighbor selection
min_class_size = min(Counter(y_filtered).values())
k_neighbors = min(2, min_class_size - 1)

print(f"⚖️ Using SMOTE with k_neighbors = {k_neighbors}")

smote = SMOTE(k_neighbors=k_neighbors, random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_filtered, y_filtered)

print("✅ SMOTE completed!")
print("New class distribution:", Counter(y_resampled))

# -----------------------------------------
# LABEL ENCODING (FOR XGBOOST)
# -----------------------------------------
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y_resampled)

with open("label_encoder.pkl", "wb") as f:
    pickle.dump(label_encoder, f)

# -----------------------------------------
# TRAIN TEST SPLIT
# -----------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X_resampled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

# -----------------------------------------
# MODEL TRAINING
# -----------------------------------------
models = {
    "Logistic Regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
    "SVM": LinearSVC(class_weight="balanced"),
    "Random Forest": RandomForestClassifier(n_estimators=200, class_weight="balanced"),
    "XGBoost": XGBClassifier(eval_metric="mlogloss")
}

best_model = None
best_score = 0

print("\n🚀 Starting Model Training...\n")

for name, model in models.items():
    print(f"⏳ Training {name}...")
    start = time.time()

    model.fit(X_train, y_train)

    end = time.time()
    print(f"✅ {name} completed in {end-start:.2f} sec")

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"📈 Accuracy: {acc:.4f}")
    print(classification_report(
        y_test,
        preds,
        target_names=label_encoder.classes_,
        zero_division=0
    ))
    print("-" * 60)

    if acc > best_score:
        best_score = acc
        best_model = model

# Save best classification model
with open("best_category_model.pkl", "wb") as f:
    pickle.dump(best_model, f)

print(f"\n🏆 Best Category Model Saved (Accuracy: {best_score:.4f})")


