import logging
from typing import Any, Text, Dict, List

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

logger= logging.getLogger(__name__)

FLASK_API_BASE= "http://localhost:5000"

def _call_api(endpoint:str, method:str="GET", playload:Dict=None) -> Dict:
    url= f"{FLASK_API_BASE}{endpoint}"
    try:
        if method=="GET":
            resp= requests.get(url, params=playload, timeout=5)
        else:
            resp= requests.get(url, json=playload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning("Flask API not reachable at %s - running in stub mode",  url)
        return {}
    except requests.exceptions.HTTPError as e:
        logger.warning("API error %s: %s", url, e)
        return {}
    
class ActionQueryBudget(Action):

    def name(self) -> Text:
        return "action_query_budget"
    
    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        category= tracker.get_slot("category")

        if not category:
            dispatcher.utter_message(
                text="Which catgeory would you like to check? "
                     "For example: Food, transport, entertainment."
            )
            return []

        data= {
            "category": category,
            "spent": 7200,
            "limit": 9000,
            "remaining": 1800,
        }

        if not data:
            dispatcher.utter_message(
                text=f"Sorry, I couldn't retrieve your {category} budget right now."
            )
            return []
        
        dispatcher.utter_message(
            text=(
                f"Your *{data['category']}* budget:\n"
                f"• Spent: ₹{data['spent']:,}\n"
                f"• Limit: ₹{data['limit']:,}\n"
                f"• Remaining: ₹{data['remaining']:,}"
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
        data = {
            "total_spent": 13000,
            "total_limit": 17000,
            "categories": [
                {"name": "Food", "spent":7200, "limit":9000},
                {"name": "Transport", "spent":1800, "limit":3500},
                {"name": "Health", "spent":900, "limit":2000},
            ],
        }

        lines= ["Here's your monthly summary:\n"]
        for cat in data["categories"]:
            pct=int(cat["spent"]/cat["limit"]*100)
            status = "🔴" if cat["spent"] > cat["limit"] else ("🟡" if pct >= 80 else "🟢")
            lines.append(
                f"{status} *{cat['name']}*: ₹{cat['spent']:,} / ₹{cat['limit']:,} ({pct}%)"
            )
        lines.append(
            f"\nTotal: ₹{data['total_spent']:,} of ₹{data['total_limit']:,} used."
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
        
        category= tracker.get_slot("category")
        amount= tracker.get_slot("amount")

        if not category or not amount:
            dispatcher.utter_message(
                text="Please tell me both the amount and category. "
                "For example: 'I spent 500 on groceries'."
            )
            return []
        
        dispatcher.utter_message(
            text=f"Got it! Logged ₹{float(amount):,.0f} under *{category}*."
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
        
        over= [
            {"category": "Entertainment", "spent":3100, "limit":2500, "over_by":600}
        ]

        if not over:
            dispatcher.utter_message(
                text="Great news - you're within budget in all categories this month 🎉"
            )
            return []
        
        lines=["⚠️ You've exceeded your budget in:\n"]
        for item in over:
            lines.append(
                f"• *{item['category']}*: spent ₹{item['spent']:,}, "
                f"limit ₹{item['limit']:,} (over by ₹{item['over_by']:,})"
            )
        lines.append("\nConsider cutting back for the rest of the month.")

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

        dispatcher.utter_message(
            text=(
                "Here are the two most effective debt reduction strategies:\n\n"
                "*Avalanche method* (saves the most money):\n"
                "Pay minimums on all debts, then put every extra rupee toward "
                "the highest-interest debt first.\n\n"
                "*Snowball method* (builds momentum):\n"
                "Pay off your smallest debt first for a quick win, then roll "
                "that payment into the next one.\n\n"
                "💡 Tip: Check if your transport or health budget has unused "
                "funds this month — redirect that surplus to your EMI."
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

        dispatcher.utter_message(
            text=(
                "A solid savings framework is the *50/30/20 rule*:\n"
                "• 50% of income → needs (rent, food, utilities)\n"
                "• 30% → wants (dining, entertainment, travel)\n"
                "• 20% → savings and debt repayment\n\n"
                "For an emergency fund, aim for 3–6 months of expenses "
                "in a liquid account before investing.\n\n"
                "💡 Tip: Automate your savings — set up a standing instruction "
                "to move 20% to savings the day your salary arrives."
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

        data = {
            "top_category": "Food",
            "top_pct": 55,
            "trend": "up",
            "insight": "Your food spending has increased 12% vs last month.",
        }

        dispatcher.utter_message(
            text=(
                f"📊 Spending analysis:\n\n"
                f"Your biggest category is *{data['top_category']}* "
                f"at {data['top_pct']}% of total tracked spend.\n"
                f"{data['insight']}\n\n"
                f"Entertainment has exceeded its cap — "
                f"consider setting a stricter limit next month."
            )
        )
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
                text="Please specify both the category and amount. "
                     "For example: 'Set my food budget to 10000'."
            )
            return []

        dispatcher.utter_message(
            text=f"Done! Your *{category}* budget is now set to ₹{float(amount):,.0f}."
        )
        return [SlotSet("category", category), SlotSet("amount", amount)]