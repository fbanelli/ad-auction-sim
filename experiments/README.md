Gender allocation experiment
---------------------------

This folder contains an experiment that demonstrates how auction economics can
make an advertiser (STEM) appear to target men more often even though they bid
symmetrically across genders.

Files:
- `experiment_gender_allocation.py`: run simulations for `first_price`,
  `second_price`, and `gsp`. Produces summary stats and optional plots (requires
  `matplotlib`).
- `auction_experiment.ipynb`: minimal notebook to interactively run the
  experiment and tweak parameters.

How to run:

    PYTHONPATH=. python3 experiments/experiment_gender_allocation.py

If you want plots, install matplotlib:

    python3 -m pip install matplotlib
