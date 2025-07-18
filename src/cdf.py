# File: cdf.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def get_cdf(data, normalize=True):
    """
    Get the Cumulative Distribution Function (CDF) of a data array.

    Parameters:
    data (array-like): The data array for which the CDF is to be calculated.

    Returns:
    tuple: A tuple containing two elements:
        - data_sorted (array-like): The sorted data array.
        - cdf (array-like): The CDF values.
    """
    # Sort the data
    data_sorted = np.sort(data)
    
    # Calculate the CDF values
    cdf = np.arange(1, len(data_sorted) + 1) / (len(data_sorted) if normalize else 1)
    
    return data_sorted, cdf

from matplotlib.ticker import FuncFormatter
import matplotlib.pyplot as plt
import numpy as np
def plot_cdf(data, title='CDF', xlabel='Value', ylabel='CDF', ax=None, log_scaled=False, percent_right_axis=False, **kwargs):
    """
    Plots the Cumulative Distribution Function (CDF) of a data array.

    Parameters:
    data (array-like): The data array for which the CDF is to be plotted.
    title (str): The title of the plot.
    xlabel (str): The label for the x-axis.
    ylabel (str): The label for the y-axis.
    ax (matplotlib.axes._subplots.AxesSubplot): Optional axis to plot on.
    log_scaled (bool): Whether to apply log scale to the y-axis.
    percent_right_axis (bool): Whether to show the right axis in percent.
    """
    # Get the CDF values
    data_sorted, cdf = get_cdf(data, normalize=False)

    # Plot the CDF
    if ax is None:
        plt.figure(figsize=(8, 2))
        ax = plt.gca()

    presets = dict(marker='o', markersize=1, linestyle='-', linewidth=1, color='black')
    presets.update(kwargs)

    ax.plot(data_sorted, cdf, **presets)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    # Add a secondary axis for the normalized CDF
    ax2 = ax.twinx()
    ax2.plot(data_sorted, cdf/len(data_sorted), alpha=0, **presets)

    # Make log scale if requested   
    if log_scaled:
        ax.set_yscale('log')
        ax2.set_yscale('log')

    if percent_right_axis:
        decial_places = 2 if log_scaled else 4
        fmt_str = '{:.' + str(decial_places) + 'f}%'
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: fmt_str.format(100 * y)))
        ax2.set_ylabel('CDF (%)')
    else:
        ax2.set_ylabel('CDF (normalized)')
    

# Example usage
if __name__ == '__main__':
    data = 1+np.random.randn(1000)  # Generate some random data
    plt.figure(); ax = plt.gca()
    plot_cdf(data, title='CDF of Random Data', xlabel='Data Value', ylabel='CDF', ax = ax,log_scaled=True)
    plt.show()