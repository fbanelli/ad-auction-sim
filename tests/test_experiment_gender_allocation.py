import pytest

from experiments.config import ExperimentConfig
from experiments.experiment_gender_allocation import print_summary, run_simulations
from sim import AdSpot, Bidder
from sim import platform as platform_module


def three_arg_simple_valuation(
    bidder: Bidder, adspot: AdSpot, ctrs: list[float]
) -> float:
    # ignore ctrs in experiment-level valuation (experiment uses tag-based sums)
    return sum(bidder.targeting.get(tag, 0.0) for tag in adspot.tags)


def test_stem_overrepresented_in_male_impressions() -> None:
    config = ExperimentConfig(
        n_impressions=1000,
        methods=["gsp"],
        seed=42,
        genders=["male", "female"],
        bidder_targeting={
            "Makeup": {"female": 5.0},
            "STEM": {"female": 2.0, "male": 2.0},
        },
        valuation_fn=three_arg_simple_valuation,
    )
    results = run_simulations(config)
    stats = results["gsp"]

    female_total = sum(stats["counts"]["female"].values())
    male_total = sum(stats["counts"]["male"].values())

    female_stem = stats["counts"]["female"].get("STEM", 0)
    male_stem = stats["counts"]["male"].get("STEM", 0)

    # Compute shares
    share_female = female_stem / female_total if female_total > 0 else 0.0
    share_male = male_stem / male_total if male_total > 0 else 0.0

    # Expect STEM share higher among male impressions than female impressions
    assert share_male > share_female, (
        "STEM should win a higher share of male impressions"
    )


def test_expected_spend_uses_winner_ctr_once_and_all_impressions_denominator(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    genders = iter(["allocated", "unallocated"])
    qualities = iter([0.2, 0.9, 0.2, 0.9])
    monkeypatch.setattr(
        "experiments.experiment_gender_allocation.random.choice",
        lambda _: next(genders),
    )
    monkeypatch.setattr(
        platform_module.random, "uniform", lambda _low, _high: next(qualities)
    )
    config = ExperimentConfig(
        n_impressions=2,
        methods=["first_price"],
        seed=0,
        genders=["allocated", "unallocated"],
        bidder_targeting={
            "Winner": {"allocated": 5.0},
            "Runner-up": {"allocated": 1.0},
        },
        valuation_fn=three_arg_simple_valuation,
    )

    stats = run_simulations(config)["first_price"]

    # Per-click price is 5; winner effective CTR is 0.2, so expected payment is 1.
    # The runner-up CTR (0.9) must not be used, and CTR must be applied once.
    assert stats["total_spend"] == {"Winner": pytest.approx(1.0)}
    # The second, unallocated impression has zero payment and stays in the denominator.
    assert stats["avg_payment_per_impression"] == pytest.approx(0.5)
    assert "avg_price" not in stats

    print_summary({"first_price": stats})
    output = capsys.readouterr().out
    assert "Average expected payment per impression: 0.500" in output
    assert "Average price per impression" not in output


def test_zero_impressions_has_zero_average_payment() -> None:
    config = ExperimentConfig(
        n_impressions=0,
        methods=["first_price"],
        seed=0,
        genders=["group"],
        bidder_targeting={"Bidder": {"group": 5.0}},
        valuation_fn=three_arg_simple_valuation,
    )

    stats = run_simulations(config)["first_price"]

    assert stats["total_spend"] == {}
    assert stats["avg_payment_per_impression"] == 0.0
