# ad-auction-sim
Ad auction simulator for Game Theory and Control class at ETH Zurich

## Quick start

Run the demo (requires Python 3.8+ and pytest installed):

	python demo.py

Run tests:

	pytest -q

The core simulator is in `sim/ad_auction.py` with classes `Bidder`, `AdSpot`, and `Platform`.

For a short tutorial on the simulator, go check out the `demo` folder! 

Recommended environment setup

We suggest using a Conda environment to keep dependencies isolated. Example quick steps:

	# create and activate a conda environment (adjust Python version as needed)
	conda create -n ad-auction-sim python=3.10 -y
	conda activate ad-auction-sim

	# install runtime and test dependencies
	pip install -r requirements.txt

Alternative (venv):

	python -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt

Notes

- This repository is a small project and is not published as an installable package by default. You don't need to install it as a package to run the demo or tests.