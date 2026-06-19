# bad_faith_detector.py
# Analyses a completed negotiation transcript for bad-faith behaviour.
# Two detectors: stalling (barely moving) and reneging (moving in wrong direction).
# Results feed into transcript_formatter.py and ultimately the GenLayer contract.


def detect_stalling(
    transcript: list[dict],
    role: str,
    tolerance: float = 0.01,
) -> list[dict]:
    """
    Flag rounds where a role's offer barely moved compared to their previous offer.

    Stalling is triggered when a role's price changes by less than `tolerance`
    (as a fraction of their previous offer) across TWO OR MORE consecutive rounds.

    Args:
        transcript: Full transcript from run_negotiation.
        role:       'buyer' or 'seller' — we only look at this role's turns.
        tolerance:  Fractional change threshold (default 1%).

    Returns:
        List of flags, each:
        {"round": int, "type": "stalling", "detail": str}
    """
    # Extract only this role's turns that have a price, in round order.
    role_turns = [
        r for r in transcript
        if r["role"] == role and r["price"] is not None
    ]

    flags = []

    # We need at least 3 turns to detect TWO consecutive tiny moves.
    if len(role_turns) < 3:
        return flags

    # Track how many consecutive small moves we've seen.
    consecutive_small = 0

    for i in range(1, len(role_turns)):
        prev_price = role_turns[i - 1]["price"]
        curr_price = role_turns[i]["price"]
        curr_round = role_turns[i]["round"]

        # Fractional change relative to previous offer (avoid div-by-zero).
        if prev_price == 0:
            continue

        change = abs(curr_price - prev_price) / prev_price

        if change < tolerance:
            consecutive_small += 1
            # Only flag from the SECOND consecutive small move onward.
            if consecutive_small >= 2:
                flags.append({
                    "round": curr_round,
                    "type":  "stalling",
                    "detail": (
                        f"{role.capitalize()} moved price by only "
                        f"{change * 100:.3f}% (${abs(curr_price - prev_price):.2f}) "
                        f"in round {curr_round} — below {tolerance * 100:.1f}% threshold "
                        f"for {consecutive_small} consecutive turns."
                    ),
                })
        else:
            # Reset streak on any meaningful move.
            consecutive_small = 0

    return flags


def detect_reneging(
    transcript: list[dict],
    role: str,
) -> list[dict]:
    """
    Flag rounds where a role's offer moves in the WRONG direction.

    - Buyer's price should only ever go UP (they concede by offering more).
    - Seller's price should only ever go DOWN (they concede by asking less).
    Any reversal is reneging.

    Args:
        transcript: Full transcript from run_negotiation.
        role:       'buyer' or 'seller'.

    Returns:
        List of flags, each:
        {"round": int, "type": "reneging", "detail": str}
    """
    role_turns = [
        r for r in transcript
        if r["role"] == role and r["price"] is not None
    ]

    flags = []

    if len(role_turns) < 2:
        return flags

    for i in range(1, len(role_turns)):
        prev_price = role_turns[i - 1]["price"]
        curr_price = role_turns[i]["price"]
        curr_round = role_turns[i]["round"]

        if role == "buyer" and curr_price < prev_price:
            # Buyer lowered their offer — moving away from seller.
            flags.append({
                "round": curr_round,
                "type":  "reneging",
                "detail": (
                    f"Buyer LOWERED offer from ${prev_price:.2f} to "
                    f"${curr_price:.2f} in round {curr_round} "
                    f"(moved away from seller by ${prev_price - curr_price:.2f})."
                ),
            })

        elif role == "seller" and curr_price > prev_price:
            # Seller raised their ask — moving away from buyer.
            flags.append({
                "round": curr_round,
                "type":  "reneging",
                "detail": (
                    f"Seller RAISED ask from ${prev_price:.2f} to "
                    f"${curr_price:.2f} in round {curr_round} "
                    f"(moved away from buyer by ${curr_price - prev_price:.2f})."
                ),
            })

    return flags


def analyze_transcript(transcript: list[dict]) -> list[dict]:
    """
    Run both detectors for both roles and return all flags sorted by round.

    Args:
        transcript: Full transcript from run_negotiation.

    Returns:
        Combined, round-sorted list of all bad-faith flags found.
        Empty list if the negotiation was clean.
    """
    flags = []

    for role in ("buyer", "seller"):
        flags.extend(detect_stalling(transcript, role))
        flags.extend(detect_reneging(transcript, role))

    # Sort by round number so the GenLayer contract reads them chronologically.
    flags.sort(key=lambda f: f["round"])

    return flags