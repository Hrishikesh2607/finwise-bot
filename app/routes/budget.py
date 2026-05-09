from flask import Blueprint, request, jsonify
from app.services.budget_service import (
    get_budget_for_category,
    get_monthly_summary,
    get_over_budget_alerts,
    set_budget_limit,
)

budget_bp= Blueprint("budget", __name__)

DEFAULT_USER_ID=1

@budget_bp.route("/<category>", methods=["GET"])
def query_budget(category):
    month=request.args.get("month")
    data= get_budget_for_category(DEFAULT_USER_ID, category, month)

    if data is None:
        return jsonify({"error": f"Category '{category}' not found"}), 404
    
    return jsonify(data), 200

@budget_bp.route("/summary", methods=["GET"])
def monthly_summary():
    month = request.args.get("month")
    data = get_monthly_summary(DEFAULT_USER_ID, month)
    return jsonify(data), 200

@budget_bp.route("/alerts", methods=["GET"])
def over_budget_alerts():
    month=request.args.get("month")
    data= get_over_budget_alerts(DEFAULT_USER_ID, month)
    return jsonify(data), 200

@budget_bp.route("/set", methods=["POST"])
def set_budget():
    body= request.get_json()

    if not body or "category" not in body or "limit" not in body:
        return jsonify({"error": "category and limit are required"}), 400
    
    try:
        limit= float(body["limit"])
    except (ValueError, TypeError):
        return jsonify({"error": "limit must be a number"}), 400
    
    data= set_budget_limit(
        DEFAULT_USER_ID,
        body["category"],
        limit,
        body.get("month"),
    ) 
    return jsonify(data), 201  