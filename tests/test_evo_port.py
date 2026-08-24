"""evo port: recipes registry + style library work in the fresh kernel."""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogym_kernel.evo.recipes import (RECIPES, EvolutionContext,
                                      propose_children)
from cogym_kernel.evo.reasoning_styles import apply_style, list_styles


def _ctx(**over):
    d = dict(elite_configs=[{"strategy": "binary"}],
             scorecard=[], hydra_leaders=[],
             search_space={"strategy": ["sequential", "binary", "reverse"]},
             rng=random.Random(5))
    d.update(over)
    return EvolutionContext(**d)


def test_all_recipes_run():
    for name in sorted(RECIPES):
        kids = propose_children(name, _ctx(), 3)
        assert len(kids) == 3, name


def test_style_sweep_varies_styles():
    ctx = _ctx(search_space={"style": ["cot", "cove"]})
    kids = propose_children("style_sweep", ctx, 4)
    assert {k["style"] for k in kids} <= {"cot", "cove"}
    assert len({k["style"] for k in kids}) == 2


def test_33_styles_apply():
    assert len(list_styles()) >= 30
    p = apply_style("decide.", "cove", seed_context="prior: overconfident")
    p_low = p.lower()
    assert ("verified" in p_low or "verification" in p_low) and "prior: overconfident" in p
