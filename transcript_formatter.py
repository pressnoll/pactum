# transcript_formatter.py
# Combines the negotiation result and bad-faith flags into a single clean
# payload that is ready to be submitted to the GenLayer intelligent contract.
# This is the exact shape the contract expects — do not change key names
# without updating the contract too.


def format_for_contract(
    negotiation_result: dict,
    bad_faith_flags: list[dict],
) -> dict:
    """
    Merge negotiation_loop output and bad_faith_detector output into one payload.

    Args:
        negotiation_result: The dict returned by run_negotiation(), containing:
                            - "transcript"  : list[dict]
                            - "outcome"     : "DEAL" | "NO_DEAL"
                            - "final_price" : float | None

        bad_faith_flags:    The list returned by analyze_transcript(), each flag:
                            - "round"  : int
                            - "type"   : "stalling" | "reneging"
                            - "detail" : str

    Returns:
        A single dict shaped for the GenLayer contract:
        {
            "transcript":      list[dict],   # full turn-by-turn history
            "outcome":         "DEAL" | "NO_DEAL",
            "final_price":     float | None,
            "bad_faith_flags": list[dict],   # empty list if negotiation was clean
        }

    Raises:
        ValueError if negotiation_result is missing required keys.
        ValueError if any flag is missing required keys.
    """

    # Validate negotiation_result shape 
    required_negotiation_keys = {"transcript", "outcome", "final_price"}
    missing = required_negotiation_keys - negotiation_result.keys()
    if missing:
        raise ValueError(
            f"negotiation_result is missing required keys: {missing}"
        )

    if negotiation_result["outcome"] not in ("DEAL", "NO_DEAL"):
        raise ValueError(
            f"outcome must be 'DEAL' or 'NO_DEAL', "
            f"got: '{negotiation_result['outcome']}'"
        )

    # Validate each transcript entry has the required keys 
    required_turn_keys = {"round", "role", "action", "price", "reasoning"}
    for i, turn in enumerate(negotiation_result["transcript"]):
        missing_turn = required_turn_keys - turn.keys()
        if missing_turn:
            raise ValueError(
                f"Transcript turn {i} is missing keys: {missing_turn}"
            )

    # Validate bad_faith_flags shape
    required_flag_keys = {"round", "type", "detail"}
    for i, flag in enumerate(bad_faith_flags):
        missing_flag = required_flag_keys - flag.keys()
        if missing_flag:
            raise ValueError(
                f"Bad-faith flag {i} is missing keys: {missing_flag}"
            )

        if flag["type"] not in ("stalling", "reneging"):
            raise ValueError(
                f"Flag {i} has unrecognised type: '{flag['type']}'. "
                f"Expected 'stalling' or 'reneging'."
            )

    # Assemble and return the contract payload
    return {
        "transcript":      negotiation_result["transcript"],
        "outcome":         negotiation_result["outcome"],
        "final_price":     negotiation_result["final_price"],
        "bad_faith_flags": bad_faith_flags,
    }


def summarise_payload(payload: dict) -> None:
    """
    Print a compact human-readable summary of the contract payload.
    Useful for debugging before you submit to GenLayer Studio.

    Args:
        payload: The dict returned by format_for_contract().
    """
    print("\n" + "=" * 60)
    print("CONTRACT PAYLOAD SUMMARY")
    print("=" * 60)
    print(f"  Outcome     : {payload['outcome']}")

    if payload["final_price"] is not None:
        print(f"  Final Price : ${payload['final_price']:.2f}")
    else:
        print(f"  Final Price : N/A")

    print(f"  Rounds      : {len(payload['transcript'])}")
    print(f"  Bad-Faith   : {len(payload['bad_faith_flags'])} flag(s)")

    if payload["bad_faith_flags"]:
        print("\n  FLAGS:")
        for flag in payload["bad_faith_flags"]:
            print(f"    [Round {flag['round']}] {flag['type'].upper()} — {flag['detail']}")

    print("=" * 60 + "\n")