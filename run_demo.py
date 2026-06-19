# run_demo.py
# Ties the entire pipeline together — runs three demo negotiations,
# detects bad faith, formats the payload, and prints everything ready
# for submission to the GenLayer contract via Studio.
#
# HOW TO USE:
# 1. Run this file locally:  python run_demo.py
# 2. Copy the "PASTE INTO STUDIO" payload printed for any demo
# 3. In GenLayer Studio, expand the "arbitrate" method
# 4. Paste the payload string into the transcript_json input field
# 5. Click "Run" — then call get_judgment() to read the result back

from negotiation_loop import run_negotiation, print_transcript
from bad_faith_detector import analyze_transcript
from transcript_formatter import format_for_contract, summarise_payload
import json


def run_demo(
    label: str,
    buyer_max_budget: float,
    seller_min_price: float,
    buyer_strategy: str,
    seller_strategy: str,
    max_rounds: int = 8,
) -> dict:
    """
    Run one full demo: negotiate → detect bad faith → format payload.

    Args:
        label:             Human-readable name for this demo run.
        buyer_max_budget:  Max the buyer will pay.
        seller_min_price:  Min the seller will accept.
        buyer_strategy:    'aggressive', 'patient', or 'fair'.
        seller_strategy:   'aggressive', 'patient', or 'fair'.
        max_rounds:        Max turns before giving up.

    Returns:
        The formatted contract payload dict.
    """
    print("\n" + "#" * 70)
    print(f"  DEMO: {label}")
    print(f"  Buyer  — max budget: ${buyer_max_budget:.2f}, strategy: {buyer_strategy}")
    print(f"  Seller — min price:  ${seller_min_price:.2f}, strategy: {seller_strategy}")
    print("#" * 70)

    # Step 1: Run the negotiation
    result = run_negotiation(
        buyer_max_budget=buyer_max_budget,
        seller_min_price=seller_min_price,
        buyer_strategy=buyer_strategy,
        seller_strategy=seller_strategy,
        max_rounds=max_rounds,
    )
    print_transcript(result)

    # Step 2: Detect bad faith 
    flags = analyze_transcript(result["transcript"])

    if flags:
        print(f"  ⚠  {len(flags)} bad-faith flag(s) detected:")
        for f in flags:
            print(f"     [Round {f['round']}] {f['type'].upper()} — {f['detail']}")
    else:
        print("  ✓  No bad-faith behaviour detected.")

    # Step 3: Format payload for contract 
    payload = format_for_contract(result, flags)
    summarise_payload(payload)

    # Step 4: Print the JSON string ready to paste into Studio 
    payload_json = json.dumps(payload, indent=2)
    print("\n" + "=" * 70)
    print("  PASTE INTO STUDIO — arbitrate() → transcript_json field:")
    print("=" * 70)
    # Studio expects a single-line JSON string in the input field
    print(json.dumps(payload))
    print("=" * 70 + "\n")

    return payload


#  Demo A: Clean deal 
# Both sides are fair, budgets overlap — should reach a clean deal with no flags.
demo_a = run_demo(
    label          = "A — Clean Deal (fair vs fair)",
    buyer_max_budget = 1000.00,
    seller_min_price =  700.00,
    buyer_strategy  = "fair",
    seller_strategy = "fair",
)

# Demo B: Deal with bad-faith flags 
# Aggressive seller barely moves — expect stalling flags.
# Budgets still overlap so a deal is possible, but the path is ugly.
demo_b = run_demo(
    label          = "B — Deal with Bad-Faith (fair buyer vs aggressive seller)",
    buyer_max_budget = 1000.00,
    seller_min_price =  700.00,
    buyer_strategy  = "fair",
    seller_strategy = "aggressive",
    max_rounds      = 10,
)

#  Demo C: No deal / walk away 
# Budgets don't overlap and both sides are aggressive — nobody will budge enough.
demo_c = run_demo(
    label          = "C — No Deal / Walk Away (aggressive vs aggressive, gap too wide)",
    buyer_max_budget =  500.00,
    seller_min_price =  900.00,
    buyer_strategy  = "aggressive",
    seller_strategy = "aggressive",
    max_rounds      = 8,
)