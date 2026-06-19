# Builds system prompts for the buyer and seller agents.

RESPONSE_FORMAT = """
You must respond ONLY in this exact format, with nothing else before or after:

ACTION: <COUNTER | ACCEPT | WALK_AWAY>
PRICE: <a number with up to 2 decimal places, or "N/A" if action is WALK_AWAY>
REASONING: <one short sentence explaining your decision>
"""

# Strategy descriptions
STRATEGY_DESCRIPTIONS = {
    "aggressive": (
        "You make large opening demands and concede very little per round. "
        "You push hard and only soften if the other party is close to your limit."
    ),
    "patient": (
        "You start modestly and make small, steady concessions over many rounds. "
        "You prefer a deal but will wait for the right price."
    ),
    "fair": (
        "You aim for a mutually acceptable middle ground. "
        "You make reasonable concessions each round and prioritise reaching a deal."
    ),
}


def build_buyer_prompt(max_budget: float, strategy: str) -> str:
    """
    Return a system prompt for the buyer agent.

    Args:
        max_budget: The absolute maximum the buyer will pay.
        strategy:   One of 'aggressive', 'patient', 'fair'.

    Returns:
        A string prompt to be prepended to each buyer turn.
    """
    strategy_text = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["fair"])

    return f"""You are a BUYER in a price negotiation.

Your maximum budget is ${max_budget:.2f}. You must NEVER agree to pay more than this.
Your goal is to buy at the lowest price possible.

Negotiation style — {strategy.upper()}:
{strategy_text}

Rules:
- If the seller's price is within your budget and you are satisfied, respond ACTION: ACCEPT.
- If you want to make a counter-offer, respond ACTION: COUNTER with your proposed PRICE.
- If the negotiation is clearly going nowhere, respond ACTION: WALK_AWAY.
- Your PRICE should always be lower than the seller's last offer (you are trying to pay less).
- Never exceed your max budget of ${max_budget:.2f}.

{RESPONSE_FORMAT}"""


def build_seller_prompt(min_price: float, strategy: str) -> str:
    """
    Return a system prompt for the seller agent.

    Args:
        min_price: The absolute minimum the seller will accept.
        strategy:  One of 'aggressive', 'patient', 'fair'.

    Returns:
        A string prompt to be prepended to each seller turn.
    """
    strategy_text = STRATEGY_DESCRIPTIONS.get(strategy, STRATEGY_DESCRIPTIONS["fair"])

    return f"""You are a SELLER in a price negotiation.

Your minimum acceptable price is ${min_price:.2f}. You must NEVER accept less than this.
Your goal is to sell at the highest price possible.

Negotiation style — {strategy.upper()}:
{strategy_text}

Rules:
- If the buyer's price meets or exceeds your minimum and you are satisfied, respond ACTION: ACCEPT.
- If you want to make a counter-offer, respond ACTION: COUNTER with your proposed PRICE.
- If the negotiation is clearly going nowhere, respond ACTION: WALK_AWAY.
- Your PRICE should always be higher than the buyer's last offer (you are trying to earn more).
- Never go below your minimum of ${min_price:.2f}.

{RESPONSE_FORMAT}"""