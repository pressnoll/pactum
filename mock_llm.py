# mock_llm.py
# Simulates LLM agent responses locally — no API calls, no cost.
# Used by negotiation_loop.py to drive both buyer and seller turns.
# All behaviour is deterministic and rule-based so tests are reproducible.

# Strategy step sizes — how much to move toward opponent each round, as a fraction of the gap.
STRATEGY_STEP = {
    "aggressive": 0.10,  # moves 10% of the gap toward opponent each round
    "patient":    0.20,  # moves 20% — steady but slow
    "fair":       0.35,  # moves 35% — actively tries to close the gap
}

# Opening position as a fraction of the agent's target price.
BUYER_OPEN_FRACTION  = 0.70   # buyer opens at 70% of their max budget
SELLER_OPEN_FRACTION = 1.30   # seller opens at 130% of their min price

ACCEPT_THRESHOLD  = 0.02   # accept if offers are within 2% of each other
WALKAWAY_ROUNDS   = 4      # earliest round a walk-away can happen
WALKAWAY_GAP      = 0.30   # walk away if still >30% apart after WALKAWAY_ROUNDS


def mock_agent_response(
    transcript: list[dict],
    role: str,
    target_price: float,
    strategy: str,
) -> str:
    """
    Simulate one agent turn and return a response string in ACTION/PRICE/REASONING format.

    Args:
        transcript:   Full negotiation history so far (list of round dicts).
        role:         'buyer' or 'seller'.
        target_price: The agent's constraint — max budget for buyer, min price for seller.
        strategy:     'aggressive', 'patient', or 'fair'.

    Returns:
        A string like:
            ACTION: COUNTER
            PRICE: 850.00
            REASONING: Moving closer to reach a deal.
    """
    step = STRATEGY_STEP.get(strategy, STRATEGY_STEP["fair"])

    # Collect this agent's own past offers and the opponent's last offer 
    my_offers   = [r["price"] for r in transcript if r["role"] == role and r["price"] is not None]
    their_offers = [r["price"] for r in transcript if r["role"] != role and r["price"] is not None]

    round_number = len(transcript) + 1  # the round we are about to play

    #  Opening move: no prior offers from either side 
    if not my_offers:
        if role == "buyer":
            price = round(target_price * BUYER_OPEN_FRACTION, 2)
            reasoning = f"Opening offer at {int(BUYER_OPEN_FRACTION * 100)}% of my budget."
        else:
            price = round(target_price * SELLER_OPEN_FRACTION, 2)
            reasoning = f"Opening ask at {int(SELLER_OPEN_FRACTION * 100)}% above my floor."
        return _format(action="COUNTER", price=price, reasoning=reasoning)

    #  Subsequent moves 
    my_last    = my_offers[-1]
    their_last = their_offers[-1] if their_offers else my_last

    # Gap as a fraction of their last offer (avoid div-by-zero)
    gap_fraction = abs(my_last - their_last) / their_last if their_last != 0 else 0

    # Check ACCEPT condition: offers within threshold AND deal is within constraint
    if gap_fraction <= ACCEPT_THRESHOLD:
        if role == "buyer" and their_last <= target_price:
            return _format("ACCEPT", their_last, "Offer is within my budget and close enough — deal.")
        if role == "seller" and their_last >= target_price:
            return _format("ACCEPT", their_last, "Offer meets my floor and the gap is small — deal.")

    # Check WALK_AWAY condition: too many rounds, gap still huge
    if round_number > WALKAWAY_ROUNDS and gap_fraction > WALKAWAY_GAP:
        return _format("WALK_AWAY", None, "Gap is too large after several rounds — walking away.")

    # Otherwise: COUNTER — move toward opponent by step * gap
    gap   = their_last - my_last   # positive if opponent is above us (buyer view), negative if below (seller view)
    move  = step * abs(gap)

    if role == "buyer":
        # Buyer moves price UP toward seller, but never above budget
        new_price = min(round(my_last + move, 2), target_price)
        reasoning = f"Raising offer by ${move:.2f} to close the gap."
    else:
        # Seller moves price DOWN toward buyer, but never below floor
        new_price = max(round(my_last - move, 2), target_price)
        reasoning = f"Lowering ask by ${move:.2f} to close the gap."

    return _format("COUNTER", new_price, reasoning)


def parse_response(raw: str) -> dict:
    """
    Parse a raw ACTION/PRICE/REASONING string into a structured dict.

    Args:
        raw: The string returned by mock_agent_response (or a real LLM).

    Returns:
        {"action": str, "price": float | None, "reasoning": str}

    Raises:
        ValueError if ACTION line is missing or unrecognised.
    """
    result = {"action": None, "price": None, "reasoning": ""}

    for line in raw.strip().splitlines():
        line = line.strip()

        if line.startswith("ACTION:"):
            action = line[len("ACTION:"):].strip().upper()
            if action not in ("COUNTER", "ACCEPT", "WALK_AWAY"):
                raise ValueError(f"Unrecognised action: '{action}'")
            result["action"] = action

        elif line.startswith("PRICE:"):
            raw_price = line[len("PRICE:"):].strip()
            if raw_price.upper() == "N/A":
                result["price"] = None
            else:
                try:
                    result["price"] = float(raw_price)
                except ValueError:
                    result["price"] = None  # degrade gracefully

        elif line.startswith("REASONING:"):
            result["reasoning"] = line[len("REASONING:"):].strip()

    if result["action"] is None:
        raise ValueError(f"Could not parse ACTION from response:\n{raw}")

    return result


# Private helper 

def _format(action: str, price: float | None, reasoning: str) -> str:
    """Format the three fields into the standard response string."""
    price_str = f"{price:.2f}" if price is not None else "N/A"
    return f"ACTION: {action}\nPRICE: {price_str}\nREASONING: {reasoning}"