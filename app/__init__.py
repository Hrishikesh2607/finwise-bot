import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

db=SQLAlchemy()
jwt=JWTManager()

def create_app():
    app=Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///finwise.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret")    

    db.init_app(app)
    jwt.init_app(app)

    CORS(app, resources={r"/*":{"origins": [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5500",
        "null",  
    ]}})

    from app.routes.budget import budget_bp
    from app.routes.transactions import transactions_bp

    app.register_blueprint(budget_bp, url_prefix="/budget")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")

    @app.route("/health")
    def health():
        return {"status":"ok", "service":"finwise-bot"}
    
    with app.app_context():
        db.create_all()

    return app