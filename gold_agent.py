# =========================================================
# Gold Agent compatibility wrapper
# Personal AI Work OS — Gold Macro Research V3.0
# =========================================================
# Keep the historical gold_agent import path stable while delegating
# all calculations and rendering to gold_macro_engine.py.

from gold_macro_engine import analyze_gold_market, render_gold_result

__all__ = ["analyze_gold_market", "render_gold_result"]
