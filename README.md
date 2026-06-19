# pactum
Pactum is an AI negotiation arbiter on GenLayer. Two AI agents haggle over price across multiple rounds, then Pactum's intelligent contract reviews the full transcript, detects bad-faith tactics like stalling or reneging, and renders a binding on-chain verdict — fair deal or foul play.

Two AI agents (buyer and seller) negotiate a price using rule-based simulated responses. Every offer, counter, and reasoning is recorded into a structured transcript. A local bad-faith detector then scans that transcript for two patterns:

- **Stalling** — barely moving an offer for two or more consecutive rounds
- **Reneging** — moving an offer backward (buyer lowering, seller raising)

The transcript and any flags are bundled into a single payload and submitted to a deployed GenLayer intelligent contract. The contract's validator LLM reads the full history, weighs the bad-faith findings, and returns a structured verdict — deal or no deal, final price, and a plain-language explanation — which validators reach consensus on before it's written to chain.

---

## Architecture

| File | Role |
|---|---|
| `agents.py` | Builds system prompts for buyer/seller, with strategy-specific negotiation styles (`aggressive`, `patient`, `fair`) |
| `mock_llm.py` | Simulates agent responses locally — opens at 70%/130% of target, concedes by strategy-based step size, accepts within 2% gap, walks away if >30% apart after 4+ rounds |
| `negotiation_loop.py` | Alternates buyer/seller turns, builds the transcript, detects DEAL/NO_DEAL outcomes |
| `bad_faith_detector.py` | Runs stalling and reneging detection across both roles, returns sorted flags |
| `transcript_formatter.py` | Validates and merges negotiation result + flags into the contract payload shape |
| `run_demo.py` | Runs three demo scenarios end to end and prints Studio-ready payloads |
| `negotiation_arbiter.py` (GenLayer contract) | The on-chain arbiter — reasons over the payload via validator LLM consensus and stores a binding judgment |

---

## Setup

### Prerequisites
- Python 3.10+
- A GenLayer Studio account ([studio.genlayer.com](https://studio.genlayer.com))

### Local setup

```bash
git clone <your-repo-url>
cd pactum
```

No external dependencies — everything in the local pipeline is Python standard library only.

### Deploy the contract

1. Open [GenLayer Studio](https://studio.genlayer.com)
2. Create a new contract file
3. Paste in the contents of `negotiation_arbiter.py`
4. Click **Deploy New Contract**
5. Note the deployed contract address

---

## Usage

### 1. Run a negotiation locally

```bash
python run_demo.py
```

This runs three demo scenarios:
- **A clean deal** (fair vs. fair)
- **A deal with bad-faith flags** (fair buyer vs. aggressive/stalling seller)
- **A walk-away** (aggressive vs. aggressive, budgets too far apart)

Each one prints a readable transcript, a bad-faith flag summary, and a single-line JSON payload ready for the contract.

### 2. Submit to the contract

1. In Studio, open your deployed contract
2. Expand the `arbitrate` write method
3. Paste the JSON payload printed by `run_demo.py` into the `transcript_json` field
4. Click **Send Transaction**
5. Wait for consensus (`Proposing → Committing → Revealing → Accepted`)

### 3. Read the verdict

Call the `get_judgment` read method to retrieve the contract's binding decision:

```json
{
  "deal_price": 833.52,
  "decision": "DEAL",
  "bad_faith_summary": "",
  "reasoning": "Both parties converged steadily and reached agreement within budget."
}
```

---

## Example Output

**Negotiation with bad-faith stalling:**
