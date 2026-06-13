import random
from datetime import datetime, timedelta
from models import SessionLocal, Merchant, User, Transaction
from auth import hash_password

db = SessionLocal()

# Step 1: Make sure a merchant exists, linked to your test user
user = db.query(User).filter(User.email == "test@test.com").first()

merchant = db.query(Merchant).filter(Merchant.user_id == user.id).first()
if not merchant:
    merchant = Merchant(name="Satya's Store", user_id=user.id)
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

print(f"Using merchant: {merchant.name} (id={merchant.id})")

# Step 2: Generate 500 random transactions
statuses = ["success", "success", "success", "success", "failed", "pending"]  # weighted towards success
locations = [1, 2, 3, 4, 5]  # pretend location codes for different cities

transactions = []
for i in range(500):
    days_ago = random.randint(0, 30)
    hour = random.randint(0, 23)
    timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hour)

    amount = round(random.uniform(100, 50000), 2)
    # occasionally create a large/suspicious amount
    if random.random() < 0.03:
        amount = round(random.uniform(100000, 500000), 2)

    txn = Transaction(
        merchant_id=merchant.id,
        amount=amount,
        status=random.choice(statuses),
        timestamp=timestamp,
        location_code=random.choice(locations),
        risk_score=0.0,
        is_flagged=False
    )
    transactions.append(txn)

db.add_all(transactions)
db.commit()

print(f"Inserted {len(transactions)} mock transactions successfully!")
db.close()