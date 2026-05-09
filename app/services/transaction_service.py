from datetime import datetime, timezone
from app import db
from app.models import Transaction, Category, User

def log_transaction(user_id:int, category_name:str, amount:float, description:str=""):
    category_name= category_name.lower().strip()

    category= Category.query.filter_by(name=category_name.capitalize()).first()
    if not category:
        category= Category(category_name.capitalize())
        db.session.add(category)
        db.session.flush()

    tx= Transaction(
        user_id=user_id,
        category_id= category.id,
        amount=amount,
        description=description,
        date=datetime.now(timezone.utc)
    )
    db.session.add(tx)
    db.session.commit()
    return tx.to_dict()

def get_transactions(user_id:int, month:str=None, category_name:str=None):
    from sqlalchemy import func

    query= Transaction.query.filter_by(user_id=user_id)

    if month:
        query= query.filter(
            func.strftime("&Y-%m", Transaction.date)==month
        )

    if category_name:
        category= Category.query.filter_by(
            name=category_name.capitalize()
        ).first()
        if category:
            query= query.filter_by(category_id=category.id)

    transactions= query.order_by(Transaction.date.desc()).all()
    return [t.to_dict() for t in transactions]
