from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import func
from app import db
from app.models import Budget, Transaction, Category, User

def get_current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")

def get_budget_for_category(user_id:int, category_name:str, month:str=None):
    month=month or get_current_month()
    category_name= category_name.lower().strip()

    category= Category.query.filter(
        func.lower(Category.name)==category_name
    ).first()

    if not Category:
        return None
    
    budget= Budget.query.filter_by(
        user_id=user_id,
        category_id=category.id,
        month=month
    ).first()

    spent_row= db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id==user_id,
        Transaction.category_id==category.id,
        func.strftime("%Y-%m", Transaction.date)==month
    ).scalar()

    spent= float(spent_row or 0)
    limit= float(budget.limit_amount) if budget else 0.0
    remaining= max(limit-spent, 0)

    return {
        "category": category.name,
        "spent":spent,
        "limit":limit,
        "remaining":remaining,
        "month":month,
        "over_budget": spent>limit,
    }

def get_monthly_summary(user_id:int, month:str=None):
    month= month or get_current_month()

    transactions= Transaction.query.filter(
        Transaction.user_id==user_id,
        func.strftime("%Y-%m", Transaction.date) == month
    ).all()

    budgets= Budget.query.filter_by(
        user_id=user_id,
        month=month
    ).all()

    if not transactions:
        return {"month":month, "total_spent":0, "categories":[]}
    
    tx_df= pd.DataFrame([
        {"category": t.category.name, "amount":t.amount}
        for t in transactions
    ])
    spent_by_cat= tx_df.groupby("category")["amount"].sum().to_dict()

    budget_map= {b.category.name: b.limit_amount for b in budgets}

    categories=[]
    for cat_name, spent in spent_by_cat.items():
        limit= budget_map.get(cat_name, 0.0)
        categories.append({
            "category": cat_name,
            "spent": round(spent, 2),
            "limit": round(limit, 2),
            "remaining": round(max(limit - spent, 0), 2),
            "over_budget": spent > limit,
            "pct_used": round((spent / limit * 100) if limit > 0 else 0, 1),
        })
    
    categories.sort(key=lambda x:x["spent"], reverse=True)

    return {
        "month":month,
        "total_spent": round(sum(spent_by_cat.values()), 2),
        "total_limit": round(sum(budget_map.values()), 2),
        "categories":categories,
    }

def get_over_budget_alerts(user_id:int, month:str=None):
    summary= get_monthly_summary(user_id, month)
    over= [c for c in summary["categories"] if c["over_budget"]]
    for item in over:
        item["over_by"]= round(item["spent"] - item["limit"], 2)
    return over

def set_budget_limit(user_id:int, category_name:str, limit:float, month:str =None):
    month= month or get_current_month()
    category_name= category_name.lower().strip()

    category= Category.query.filter(
        func.lower(Category.name)==category_name
    ).first()

    if not category:
        category= Category(name=category_name.capitalize())
        db.session.add(category)
        db.session.flush()

    budget= Budget.query.filter_by(
        user_id=user_id,
        category_id=category.id,
        month=month
    ).first()

    if budget:
        budget.limit_amount= limit
    else:
        budget= Budget(
            user_id=user_id,
            category_id=category.id,
            limit_amount=limit,
            month=month
        )
        db.session.add(budget)

    db.session.commit()
    return {"category":category_name, "limit":limit, "month":month}