from flask import Blueprint, request, jsonify
from app.services.transaction_service import log_transaction, get_transactions

transactions_bp= Blueprint("transactions", __name__)

DEFAULT_USER_ID=1

@transactions_bp.route("", methods=["POST"])
def add_transaction():
    body= request.get_json()

    if not body or "category" not in body or "amount" not in body:
        return jsonify({"error": "category and amount are required"}), 400
    
    try:
        amount= float(body["amount"])
    except (ValueError, TypeError):
        return jsonify({"error": "amount must be a number"}), 400
    
    if amount<=0:
        return jsonify({"error":"amount must be greater than zero"}), 400
    
    data= log_transaction(
        DEFAULT_USER_ID,
        body["category"],
        amount,
        body.get("description", ""),
    )
    return jsonify(data), 201

@transactions_bp.route("", methods=["GET"])
def list_transactions():
    month= request.args.get("month")
    category= request.args.get("category")
    data= get_transactions(DEFAULT_USER_ID, month, category)
    return jsonify(data), 200