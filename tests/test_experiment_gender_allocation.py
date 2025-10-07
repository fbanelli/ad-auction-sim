from experiments.experiment_gender_allocation import run_simulations


def three_arg_simple_valuation(bidder, adspot, ctrs):
    # ignore ctrs in experiment-level valuation (experiment uses tag-based sums)
    return sum(bidder.targeting.get(tag, 0.0) for tag in adspot.tags)


def test_stem_overrepresented_in_male_impressions():
    results = run_simulations(n_impressions=1000, methods=["second_price"], seed=42, valuation_fn=three_arg_simple_valuation)
    stats = results["second_price"]

    female_total = sum(stats["counts"]["female"].values())
    male_total = sum(stats["counts"]["male"].values())

    female_stem = stats["counts"]["female"].get("STEM", 0)
    male_stem = stats["counts"]["male"].get("STEM", 0)

    # Compute shares
    share_female = female_stem / female_total if female_total > 0 else 0.0
    share_male = male_stem / male_total if male_total > 0 else 0.0

    # Expect STEM share higher among male impressions than female impressions
    assert share_male > share_female
