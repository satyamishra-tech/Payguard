import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
from models import SessionLocal, Transaction

db = SessionLocal()

# Step 1: Load all transactions into a DataFrame
transactions = db.query(Transaction).all()

data = []
for t in transactions:
    data.append({
        "id": t.id,
        "amount": t.amount,
        "hour": t.timestamp.hour,
        "location_code": t.location_code
    })

df = pd.DataFrame(data)
print(f"Loaded {len(df)} transactions")
print(df.head())

# Step 2: Prepare features for training
X = df[["amount", "hour", "location_code"]]

# Step 3: Train Isolation Forest
model = IsolationForest(contamination=0.05, random_state=42)
model.fit(X)

# Step 4: Save the trained model
joblib.dump(model, "fraud_model.pkl")
print("Model trained and saved as fraud_model.pkl")

# Step 5: Score all existing transactions and update the database
scores = model.decision_function(X)  # raw anomaly scores (higher = more normal)
predictions = model.predict(X)       # -1 = anomaly, 1 = normal

# Convert decision_function scores to a 0-100 risk score (inverted: higher = riskier)
min_score, max_score = scores.min(), scores.max()
risk_scores = 100 * (max_score - scores) / (max_score - min_score)

updated_count = 0
for i, t in enumerate(transactions):
    t.risk_score = round(float(risk_scores[i]), 2)
    t.is_flagged = bool(predictions[i] == -1)
    if t.is_flagged:
        updated_count += 1

db.commit()
print(f"Updated risk scores for all transactions. {updated_count} flagged as suspicious.")
db.close()