import os
from collections import Counter
import tempfile
import shutil
import random
import matplotlib
import pytest

from sim.ad_auction import AdSpot, Bidder, Platform
from experiments.experiment_gender_allocation import run_simulations, print_summary, try_plot, simple_valuation


def test_adspot_invalid_pos_values():
    # pos values must be within [0,1]
    with pytest.raises(ValueError):
        AdSpot(2, ["a"], pos=[1.2, 0.5])


def test_assign_qs_length_mismatch():
    a = AdSpot(1, ["a"]) 
    b = Bidder("X", {"a": 1.0})
    # Call assign with Qs length not matching bidders
    with pytest.raises(ValueError):
        a.assign([b], method="second_price", valuation_fn=lambda bidder, adspot, ctrs: 1.0, Qs=[0.5, 0.6])


def test_run_simulations_and_print_and_plot(tmp_path, monkeypatch, capsys):
    # Run a small number of impressions to exercise run_simulations
    random.seed(0)
    results = run_simulations(n_impressions=10, methods=["second_price"], seed=0, valuation_fn=simple_valuation)
    assert "second_price" in results
    # Exercise print_summary (capture stdout)
    print_summary(results)
    captured = capsys.readouterr()
    assert "Total impressions" in captured.out

    # Exercise try_plot: use a temporary output dir
    out_dir = tmp_path / "out"
    try_plot(results, out_prefix=str(out_dir))
    # Verify that files were created for the method
    files = list(out_dir.glob("*.png"))
    assert len(files) >= 1
    # Clean up by removing tmpdir (pytest will handle tmp_path cleanup)


def test_run_simulations_default_methods_and_none_winner():
    # methods default path when methods is None
    # use valuation_fn that returns 0 to force 'none' winners and exercise counts[gender]["none"]
    results = run_simulations(n_impressions=5, methods=None, seed=1, valuation_fn=lambda b, a, ctrs: 0.0)
    # Ensure default methods keys present
    assert all(m in results for m in ["first_price", "second_price", "gsp"])
    # Check that 'none' appears in counts for genders
    for stats in results.values():
        assert stats["counts"]["male"]["none"] + stats["counts"]["female"]["none"] == 5


def test_try_plot_exception_path(monkeypatch, capsys, tmp_path):
    # Cause matplotlib.pyplot.subplots to raise so try_plot hits the except block
    import matplotlib.pyplot as plt

    def bad_subplots(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(plt, "subplots", bad_subplots)

    # build a tiny fake results dict similar to run_simulations output
    fake_results = {
        "m": {
            "counts": {"female": {"A": 1}, "male": {"A": 0}},
            "shares": {"female": {"A": 1.0}, "male": {"A": 0.0}},
            "total_spend": {},
            "avg_price": 0.0,
            "n_impressions": 1,
        }
    }

    try_plot(fake_results, out_prefix=str(tmp_path))
    captured = capsys.readouterr()
    assert "Plotting skipped" in captured.out


def test_module_main_executes(monkeypatch):
    # Execute experiments module as __main__ with monkeypatched heavy functions to hit the __main__ block
    import runpy

    # patch run_simulations, print_summary, try_plot to lightweight stubs
    import experiments.experiment_gender_allocation as ega

    monkeypatch.setattr(ega, "run_simulations", lambda n_impressions, methods, seed: {"x": {"counts": {"male": {}, "female": {}}, "shares": {"male": {}, "female": {}}, "total_spend": {}, "avg_price": 0.0, "n_impressions": n_impressions}})
    monkeypatch.setattr(ega, "print_summary", lambda results: None)
    monkeypatch.setattr(ega, "try_plot", lambda results: None)

    # Running module as __main__ should execute the block without error
    # suppress the RuntimeWarning about module already present in sys.modules
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*found in sys.modules.*", category=RuntimeWarning)
        runpy.run_module("experiments.experiment_gender_allocation", run_name="__main__")