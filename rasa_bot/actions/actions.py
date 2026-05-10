import logging
from typing import Any, Text, Dict, List

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

FLASK_API_BASE = "http://localhost:5000"


def _call_api(endpoint: str, method: str = "GET", payload: Dict = None) -> Dict | None:
    url = f"{FLASK_API_BASE}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=payload, timeout=5)
        else:
            resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.error("Flask API unreachable at %s", url)
        return None
    except requests.exceptions.Timeout:
        logger.error("Flask API timed out at %s", url)
        return None
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error at %s: %s", url, e)
        return None
    except Exception as e:
        logger.error("Unexpected error calling %s: %s", url, e)
        return None


def _api_error_message(dispatcher: CollectingDispatcher, action: str) -> None:
    dispatcher.utter_message(
        text=(
            "Sorry, I'm having trouble reaching the finance backend right now. "
            "Please make sure the Flask server is running on port 5000."
        )
    )
    logger.warning("Action '%s' failed — Flask API returned None", action)


class ActionQueryBudget(Action):

    def name(self) -> Text:
        return "action_query_budget"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        category = tracker.get_slot("category")

        if not category:
            dispatcher.utter_message(
                text="Which category would you like to check? "
                     "For example: food, transport, or entertainment."
            )
            return []

        data = _call_api(f"/budget/{category.lower()}")

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        if "error" in data:
            dispatcher.utter_message(
                text=f"I couldn't find a budget for *{category}*. "
                     "Try setting one first — for example: "
                     "'Set my food budget to 9000'."
            )
            return []

        pct = int((data["spent"] / data["limit"] * 100)) if data["limit"] > 0 else 0
        status = "🔴 Over budget" if data["over_budget"] else ("🟡 Almost there" if pct >= 80 else "🟢 On track")

        dispatcher.utter_message(
            text=(
                f"*{data['category']}* budget for {data['month']}:\n"
                f"• Spent: ₹{data['spent']:,.0f}\n"
                f"• Limit: ₹{data['limit']:,.0f}\n"
                f"• Remaining: ₹{data['remaining']:,.0f} ({pct}% used)\n"
                f"• Status: {status}"
            )
        )
        return [SlotSet("category", category)]


class ActionMonthlySummary(Action):

    def name(self) -> Text:
        return "action_monthly_summary"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        data = _call_api("/budget/summary")

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        if not data.get("categories"):
            dispatcher.utter_message(
                text="No transactions found for this month yet. "
                     "Start by logging an expense — for example: "
                     "'I spent 500 on groceries'."
            )
            return []

        lines = [f"📊 *Summary for {data['month']}*\n"]
        for cat in data["categories"]:
            pct = cat["pct_used"]
            status = "🔴" if cat["over_budget"] else ("🟡" if pct >= 80 else "🟢")
            lines.append(
                f"{status} *{cat['category']}*: "
                f"₹{cat['spent']:,.0f} / ₹{cat['limit']:,.0f} ({pct}%)"
            )

        pct_total = (
            int(data["total_spent"] / data["total_limit"] * 100)
            if data["total_limit"] > 0 else 0
        )
        lines.append(
            f"\n💰 Total: ₹{data['total_spent']:,.0f} of "
            f"₹{data['total_limit']:,.0f} ({pct_total}% used)"
        )

        dispatcher.utter_message(text="\n".join(lines))
        return []


class ActionAddTransaction(Action):

    def name(self) -> Text:
        return "action_add_transaction"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        category = tracker.get_slot("category")
        amount = tracker.get_slot("amount")

        if not category or not amount:
            dispatcher.utter_message(
                text="Please include both the amount and category. "
                     "For example: 'I spent 500 on groceries'."
            )
            return []

        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            dispatcher.utter_message(text="That amount doesn't look right. Please use a number.")
            return []

        if amount_float <= 0:
            dispatcher.utter_message(text="Amount must be greater than zero.")
            return []

        data = _call_api(
            "/transactions",
            method="POST",
            payload={"category": category, "amount": amount_float},
        )

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        dispatcher.utter_message(
            text=(
                f"✅ Logged ₹{amount_float:,.0f} under *{data['category']}* "
                f"on {data['date']}."
            )
        )

        budget_check = _call_api(f"/budget/{category.lower()}")
        if budget_check and budget_check.get("over_budget"):
            dispatcher.utter_message(
                text=(
                    f"⚠️ Heads up — you've now exceeded your *{category}* budget! "
                    f"You're ₹{abs(budget_check['remaining']):,.0f} over the limit."
                )
            )

        return [SlotSet("category", category), SlotSet("amount", amount)]


class ActionOverBudgetAlert(Action):

    def name(self) -> Text:
        return "action_over_budget_alert"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        data = _call_api("/budget/alerts")

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        if not data:
            dispatcher.utter_message(
                text="🎉 Great news — you're within budget in every category this month!"
            )
            return []

        lines = ["⚠️ *Over-budget categories this month:*\n"]
        for item in data:
            lines.append(
                f"🔴 *{item['category']}*: "
                f"spent ₹{item['spent']:,.0f} vs limit ₹{item['limit']:,.0f} "
                f"(over by ₹{item['over_by']:,.0f})"
            )
        lines.append(
            "\n💡 Tip: Redirect unused budget from other categories to cover the gap."
        )

        dispatcher.utter_message(text="\n".join(lines))
        return []


class ActionDebtAdvice(Action):

    def name(self) -> Text:
        return "action_debt_advice"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        summary = _call_api("/budget/summary")
        surplus_tip = ""

        if summary and summary.get("categories"):
            surplus_cats = [
                c for c in summary["categories"]
                if not c["over_budget"] and c["remaining"] > 500
            ]
            if surplus_cats:
                top = max(surplus_cats, key=lambda x: x["remaining"])
                surplus_tip = (
                    f"\n\n💡 Your *{top['category']}* budget has "
                    f"₹{top['remaining']:,.0f} unused this month — "
                    f"consider redirecting it to your EMI payment."
                )

        dispatcher.utter_message(
            text=(
                "Here are the two most effective debt reduction strategies:\n\n"
                "*Avalanche method* (saves the most money):\n"
                "Pay minimums on all debts, then put every extra rupee toward "
                "the highest-interest debt first.\n\n"
                "*Snowball method* (builds momentum):\n"
                "Pay off your smallest debt first for a quick win, then roll "
                "that payment into the next one."
                f"{surplus_tip}"
            )
        )
        return []


class ActionSavingsAdvice(Action):

    def name(self) -> Text:
        return "action_savings_advice"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        summary = _call_api("/budget/summary")
        savings_line = ""

        if summary:
            total_spent = summary.get("total_spent", 0)
            total_limit = summary.get("total_limit", 0)
            surplus = total_limit - total_spent
            if surplus > 0:
                savings_line = (
                    f"\n\n💰 Based on this month, you have "
                    f"₹{surplus:,.0f} of unspent budget — "
                    f"a great candidate for your savings account."
                )

        dispatcher.utter_message(
            text=(
                "A solid savings framework is the *50/30/20 rule*:\n"
                "• 50% of income → needs (rent, food, utilities)\n"
                "• 30% → wants (dining, entertainment, travel)\n"
                "• 20% → savings and debt repayment\n\n"
                "For an emergency fund, aim for 3–6 months of expenses "
                "in a liquid account before investing.\n\n"
                "⚙️ Tip: Automate your savings — set a standing instruction "
                "to move 20% to savings the day your salary arrives."
                f"{savings_line}"
            )
        )
        return []


class ActionSpendingAnalysis(Action):

    def name(self) -> Text:
        return "action_spending_analysis"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        data = _call_api("/budget/summary")

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        if not data.get("categories"):
            dispatcher.utter_message(
                text="No spending data found for this month yet."
            )
            return []

        categories = data["categories"]
        top = categories[0]
        over = [c for c in categories if c["over_budget"]]
        healthy = [c for c in categories if not c["over_budget"] and c["pct_used"] < 60]

        lines = [f"📊 *Spending analysis for {data['month']}*\n"]

        lines.append(
            f"🏆 Biggest category: *{top['category']}* — "
            f"₹{top['spent']:,.0f} ({top['pct_used']}% of its budget)"
        )

        if over:
            over_names = ", ".join(f"*{c['category']}*" for c in over)
            lines.append(f"🔴 Over budget: {over_names}")

        if healthy:
            healthy_names = ", ".join(f"*{c['category']}*" for c in healthy)
            lines.append(f"🟢 Well within limit: {healthy_names}")

        lines.append(
            f"\n💰 Total spent: ₹{data['total_spent']:,.0f} "
            f"of ₹{data['total_limit']:,.0f}"
        )

        dispatcher.utter_message(text="\n".join(lines))
        return []


class ActionSetBudget(Action):

    def name(self) -> Text:
        return "action_set_budget"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        category = tracker.get_slot("category")
        amount = tracker.get_slot("amount")

        if not category or not amount:
            dispatcher.utter_message(
                text="Please tell me both the category and the amount. "
                     "For example: 'Set my food budget to 10000'."
            )
            return []

        try:
            limit = float(amount)
        except (ValueError, TypeError):
            dispatcher.utter_message(text="That amount doesn't look right. Please use a number.")
            return []

        data = _call_api(
            "/budget/set",
            method="POST",
            payload={"category": category, "limit": limit},
        )

        if data is None:
            _api_error_message(dispatcher, self.name())
            return []

        dispatcher.utter_message(
            text=(
                f"✅ Done! Your *{data['category']}* budget for "
                f"{data['month']} is now set to ₹{data['limit']:,.0f}."
            )
        )
        return [SlotSet("category", category), SlotSet("amount", amount)]