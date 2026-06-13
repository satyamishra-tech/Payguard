from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, SessionLocal
from auth import hash_password, verify_password, create_access_token, decode_access_token

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}

from fastapi import Query
from models import Merchant, Transaction
from typing import Optional


@app.get("/transactions")
def get_transactions(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()
    query = db.query(Transaction).filter(Transaction.merchant_id == merchant.id)

    if status:
        query = query.filter(Transaction.status == status)

    if search:
        query = query.filter(Transaction.id == int(search)) if search.isdigit() else query

    total = query.count()
    transactions = query.order_by(Transaction.timestamp.desc()) \
                         .offset((page - 1) * page_size) \
                         .limit(page_size) \
                         .all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "status": t.status,
                "timestamp": t.timestamp,
                "risk_score": t.risk_score,
                "is_flagged": t.is_flagged
            }
            for t in transactions
        ]
    }

    from sqlalchemy import func
from datetime import datetime, timedelta


@app.get("/analytics/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()

    base_query = db.query(Transaction).filter(Transaction.merchant_id == merchant.id)

    total_transactions = base_query.count()

    total_revenue = db.query(func.sum(Transaction.amount)) \
        .filter(Transaction.merchant_id == merchant.id, Transaction.status == "success") \
        .scalar() or 0

    flagged_count = base_query.filter(Transaction.is_flagged == True).count()

    success_count = base_query.filter(Transaction.status == "success").count()
    success_rate = round((success_count / total_transactions) * 100, 1) if total_transactions > 0 else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_transactions": total_transactions,
        "flagged_count": flagged_count,
        "success_rate": success_rate
    }


@app.get("/analytics/daily")
def get_daily_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    results = db.query(
        func.date(Transaction.timestamp).label("date"),
        func.sum(Transaction.amount).label("revenue"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.merchant_id == merchant.id,
        Transaction.timestamp >= thirty_days_ago
    ).group_by(
        func.date(Transaction.timestamp)
    ).order_by(
        func.date(Transaction.timestamp)
    ).all()

    return {
        "daily": [
            {
                "date": str(row.date),
                "revenue": round(row.revenue, 2),
                "count": row.count
            }
            for row in results
        ]
    }


@app.get("/analytics/status-breakdown")
def get_status_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter(Merchant.user_id == current_user.id).first()

    results = db.query(
        Transaction.status,
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.merchant_id == merchant.id
    ).group_by(Transaction.status).all()

    return {
        "breakdown": [
            {"status": row.status, "count": row.count}
            for row in results
        ]
    }