# negotiation_loop.py
# Drives the back-and-forth negotiation between buyer and seller.
# Calls mock_llm.py for both agents and builds the transcript that
# bad_faith_detector.py and the GenLayer contract will later consume.

from mock_llm import mock_agent_response, parse_response


def run_negotiation(
    buyer_max_budget: float,
    seller_min_price: float,
    buyer_strategy: str = "fair",
    seller_strategy: str = "fair",
    max_rounds: int = 8,
) -> dict:
    """
    Run a full negotiation between buyer and seller.

    Args:
        buyer_max_budget:  The most the buyer will ever pay.
        seller_min_price:  The least the seller will ever accept.
        buyer_strategy:    'aggressive', 'patient', or 'fair'.
        seller_strategy:   'aggressive', 'patient', or 'fair'.
        max_rounds:        Hard cap on total rounds (buyer + seller turns combined).

    Returns:
        {
            "transcript": list[dict],   # every turn, in order
            "outcome":    "DEAL" | "NO_DEAL",
            "final_price": float | None
        }

    Each transcript dict has EXACTLY these keys:
        "round"     : int   — 1-indexed turn counter
        "role"      : str   — "buyer" or "seller"
        "action"    : str   — "COUNTER", "ACCEPT", or "WALK_AWAY"
        "price"     : float | None
        "reasoning" : str
    """
    transcript   = []
    outcome      = "NO_DEAL"
    final_price  = None

    # Turns alternate: buyer goes first, then seller, then buyer, ...
    # We count each individual turn as a "round" (so max_rounds=8 means
    # up to 4 buyer turns and 4 seller turns).
    for turn in range(1, max_rounds + 1):
        role     = "buyer" if turn % 2 == 1 else "seller"
        t_price  = buyer_max_budget if role == "buyer" else seller_min_price
        strategy = buyer_strategy   if role == "buyer" else seller_strategy

        #  Get and parse the agent's response 
        raw      = mock_agent_response(transcript, role, t_price, strategy)
        parsed   = parse_response(raw)

        # Record the turn
        turn_record = {
            "round":     turn,
            "role":      role,
            "action":    parsed["action"],
            "price":     parsed["price"],
            "reasoning": parsed["reasoning"],
        }
        transcript.append(turn_record)

        # Check for terminal actions 
        if parsed["action"] == "WALK_AWAY":
            outcome     = "NO_DEAL"
            final_price = None
            break

        if parsed["action"] == "ACCEPT":
            # The accepting party agrees to the OTHER side's last stated price.
            # Find the opponent's most recent price offer.
            opponent_role = "seller" if role == "buyer" else "buyer"
            opponent_prices = [
                r["price"] for r in transcript
                if r["role"] == opponent_role and r["price"] is not None
            ]

            if opponent_prices:
                final_price = opponent_prices[-1]
            else:
                # Edge case: opponent never made an offer (shouldn't happen
                # in normal flow, but handle it gracefully).
                final_price = parsed["price"]

            outcome = "DEAL"
            break

    # If we exhausted all rounds without ACCEPT or WALK_AWAY it's NO_DEAL.
    return {
        "transcript":  transcript,
        "outcome":     outcome,
        "final_price": final_price,
    }


def print_transcript(result: dict) -> None:
    """
    Print a negotiation result in a readable format to stdout.

    Args:
        result: The dict returned by run_negotiation.
    """
    print("\n" + "=" * 60)
    print("NEGOTIATION TRANSCRIPT")
    print("=" * 60)

    for entry in result["transcript"]:
        price_str = f"${entry['price']:.2f}" if entry["price"] is not None else "N/A"
        print(
            f"  Round {entry['round']:>2} | {entry['role'].upper():<6} | "
            f"{entry['action']:<10} | {price_str:<10} | {entry['reasoning']}"
        )

    print("-" * 60)
    print(f"  OUTCOME    : {result['outcome']}")
    if result["final_price"] is not None:
        print(f"  FINAL PRICE: ${result['final_price']:.2f}")
    print("=" * 60 + "\n")