"""Standalone figures generated only from recorded CSVs."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def generate_charts(results):
    results = Path(results)
    history = pd.read_csv(results / 'training_history.csv')
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    for ax, metric in zip(axes.flat, ('reward', 'avg_wait', 'avg_queue', 'epsilon', 'served', 'visited_states')):
        ax.plot(history.episode, history[metric], alpha=.4, label='Recorded')
        if metric != 'epsilon':
            ax.plot(history.episode, history[metric].rolling(50, min_periods=1).mean(), label='50 episode mean')
        ax.set(xlabel='Episode', ylabel=metric)
        ax.legend()
    fig.tight_layout()
    fig.savefig(results / 'training_charts.png', dpi=140)
    plt.close(fig)
    data = pd.read_csv(results / 'evaluation_results.csv')
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, metric in zip(axes.flat, ('avg_wait', 'avg_queue', 'served', 'reward')):
        data.groupby(['scenario', 'controller'])[metric].mean().unstack().plot.bar(ax=ax, rot=15)
        ax.set_ylabel(metric)
    fig.tight_layout()
    fig.savefig(results / 'comparison_charts.png', dpi=140)
    plt.close(fig)
