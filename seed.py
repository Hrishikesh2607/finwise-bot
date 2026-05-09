from app import create_app, db
from app.models import User, Category, Budget, Transaction
from datetime import datetime, timedelta, timezone
import random

app= create_app()

CATEGORIES= ["Food", "Transport", "Entertainment", "Health", "Shopping", "Utilities"]
BUDGETS= {
    "Food":9000, "Transport":3500, "Entertainment":2500,
    "Health":2000, "Shopping":4000, "Utilities":2000
}
CURRENT_MONTH=datetime.now(timezone.utc).strftime("%Y-%m")

with app.app_context():
    db.drop_all()
    db.create_all()

    user= User(username="testuser", email="test@finwise.com")
    db.session.add(user)
    db.session.flush()

    for name in CATEGORIES:
        cat= Category(name=name)
        db.session.add(cat)
    db.session.flush()

    for name, limit in BUDGETS.items():
        cat= Category.query.filter_by(name=name).first()
        budget= Budget(
            user_id=user.id,
            category_id=cat.id,
            limit_amount=limit,
            month= CURRENT_MONTH
        )
        db.session.add(budget)

    sample_transactions= [
          ("Food", 1200), ("Food", 850), ("Food", 2100), ("Food", 950),
        ("Food", 1400), ("Food", 700),
        ("Transport", 500), ("Transport", 800), ("Transport", 500),
        ("Entertainment", 1200), ("Entertainment", 900), ("Entertainment", 1000),
        ("Health", 450), ("Health", 450),
        ("Shopping", 1500), ("Utilities", 1100),
    ]

    for cat_name, amount in sample_transactions:
        cat = Category.query.filter_by(name=cat_name).first()
        days_ago = random.randint(0, 27)
        tx = Transaction(
            user_id=user.id,
            category_id=cat.id,
            amount=amount,
            description=f"{cat_name} expense",
            date=datetime.utcnow() - timedelta(days=days_ago)
        )
        db.session.add(tx)

    db.session.commit()
    print("✅ Database seeded successfully.")
    print(f"   User: testuser | Categories: {len(CATEGORIES)} | Transactions: {len(sample_transactions)}")