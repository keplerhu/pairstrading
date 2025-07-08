# Pairs Trading Project

This repository implements a mean-reversion trading strategy based on cointegration between asset pairs. It includes:

- Cointegration testing using the Engle-Granger method
- Spread construction with hedge ratio
- Z-score-based signal generation
- Grid search for optimal entry/exit thresholds
- Backtesting using Yahoo Finance data
- Production implementation in the CloudQuant backtesting engine


## Goal
I wanted to gain experience creating and backtesting a basic strategy from scratch using Jupyter Notebooks and Python. I had noticed that the one minute charts of RCAT and UMAC looked like they were following eachother on a day with drone news and I wanted to see if there was a strategy behind it. 

## Key Takeaways
- Learned how to test for cointegration using the Engle-Granger method
- Developed a rolling spread-based signal using z-scores
- Implemented a grid search to optimize entry/exit parameters
- Translated a Jupyter prototype into a production-ready script using CloudQuant
- Worked with live data from Yahoo Finance and real-world backtesting infrastructure

## Contents
- notebooks/pairstrading.ipynb: Research and strategy development
- scripts/umacrcatpairstrader.py: Production-ready script that runs in cloudquant. 
- scripts/tradescsvtosharpe.py: Analyzes and plots the returns from the csv of trades from cloudquant backtest
- results/tradescq122.csv: Raw csv output of trades taken during cloudquant simulation

