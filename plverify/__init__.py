"""plverify — the model proposes; PL disposes.
A verification harness for math derivations: never a solver, always a
grader. Verdicts are tiered, priced, and sealed."""
from .verify import verify
from .core import Verdict, Step, seal, replay, weakest, TIER_ORDER
__all__ = ["verify", "Verdict", "Step", "seal", "replay", "weakest",
           "TIER_ORDER"]
