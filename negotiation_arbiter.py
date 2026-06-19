# v0.2.16
# { "Depends": "" }
from genlayer import *
import json


class NegotiationArbiter(gl.Contract):

    last_judgment: str

    def __init__(self):
        self.last_judgment = ""

    @gl.public.write
    def arbitrate(self, transcript_json: str) -> None:

        try:
            payload = json.loads(transcript_json)
        except json.JSONDecodeError:
            raise gl.vm.UserError("Invalid JSON payload.")

        required_keys = {"transcript", "outcome", "final_price", "bad_faith_flags"}
        missing = required_keys - payload.keys()
        if missing:
            raise gl.vm.UserError(f"Payload missing required keys: {list(missing)}")

        outcome         = payload["outcome"]
        final_price     = payload["final_price"]
        transcript      = payload["transcript"]
        bad_faith_flags = payload["bad_faith_flags"]

        prompt = _build_arbiter_prompt(outcome, final_price, transcript, bad_faith_flags)

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")

            if not isinstance(result, dict):
                raise gl.vm.UserError(f"LLM returned non-dict: {type(result)}")

            # Normalize alternate key names the LLM might use
            if "deal_price" not in result:
                for alt in ("price", "final_price", "agreed_price", "settlement_price", "deal_amount"):
                    if alt in result:
                        result["deal_price"] = result[alt]
                        break
                else:
                    result["deal_price"] = None

            if "bad_faith_summary" not in result:
                for alt in ("bad_faith", "bad_faith_notes", "flags_summary", "summary", "bad_faith_findings"):
                    if alt in result:
                        result["bad_faith_summary"] = result[alt]
                        break
                else:
                    result["bad_faith_summary"] = ""

            if "reasoning" not in result:
                for alt in ("reason", "explanation", "justification", "notes", "rationale"):
                    if alt in result:
                        result["reasoning"] = result[alt]
                        break
                else:
                    result["reasoning"] = ""

            if "decision" not in result:
                raise gl.vm.UserError("LLM did not return a decision field.")

            decision = str(result["decision"]).upper().strip()
            if decision not in ("DEAL", "NO_DEAL"):
                if decision in ("YES", "AGREED", "ACCEPTED", "ACCEPT"):
                    decision = "DEAL"
                elif decision in ("NO", "REJECTED", "FAILED", "WALK_AWAY", "WALKAWAY"):
                    decision = "NO_DEAL"
                else:
                    raise gl.vm.UserError(f"LLM returned invalid decision: '{result['decision']}'")
            result["decision"] = decision

            return result

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            data = leader_result.calldata

            if not isinstance(data, dict):
                return False

            required_judgment_keys = {
                "deal_price", "decision", "bad_faith_summary", "reasoning"
            }
            if not required_judgment_keys.issubset(data.keys()):
                return False

            if data["decision"] not in ("DEAL", "NO_DEAL"):
                return False

            if not isinstance(data.get("bad_faith_summary"), str):
                return False

            if not isinstance(data.get("reasoning"), str):
                return False

            return True

        judgment = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.last_judgment = json.dumps(judgment)

    @gl.public.view
    def get_judgment(self) -> str:
        return self.last_judgment

    @gl.public.view
    def has_judgment(self) -> bool:
        return self.last_judgment != ""


def _build_arbiter_prompt(
    outcome: str,
    final_price,
    transcript: list,
    bad_faith_flags: list,
) -> str:

    transcript_lines = []
    for turn in transcript:
        price_str = f"${turn['price']:.2f}" if turn.get("price") is not None else "N/A"
        transcript_lines.append(
            f"  Round {turn['round']} | {turn['role'].upper():<6} | "
            f"{turn['action']:<10} | {price_str:<10} | {turn['reasoning']}"
        )
    transcript_text = "\n".join(transcript_lines) if transcript_lines else "  (empty)"

    if bad_faith_flags:
        flag_lines = [
            f"  [Round {f['round']}] {f['type'].upper()} — {f['detail']}"
            for f in bad_faith_flags
        ]
        flags_text = "\n".join(flag_lines)
    else:
        flags_text = "  None detected."

    price_line = f"${final_price:.2f}" if final_price is not None else "null"

    return f"""You are a neutral arbitration judge reviewing a price negotiation.

NEGOTIATION TRANSCRIPT:
{transcript_text}

REPORTED OUTCOME: {outcome}
REPORTED FINAL PRICE: {price_line}

BAD-FAITH FLAGS:
{flags_text}

YOUR TASK:
Produce a final binding judgment as a JSON object.

You MUST use EXACTLY these four key names — no others:
- "deal_price": the agreed price as a number, or null if no deal
- "decision": exactly the string "DEAL" or exactly the string "NO_DEAL"
- "bad_faith_summary": plain English string describing bad-faith findings, or "" if none
- "reasoning": 1-2 sentences explaining your decision

IMPORTANT: Return ONLY the JSON object. No markdown. No explanation outside the JSON.

Example of correct output:
{{"deal_price": null, "decision": "NO_DEAL", "bad_faith_summary": "Seller stalled in rounds 8 and 10.", "reasoning": "No deal was reached. The seller showed bad-faith stalling behaviour."}}"""