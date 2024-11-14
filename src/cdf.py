import numpy as np

import matplotlib.pyplot as plt

def get_cdf(data):
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
    cdf = np.arange(1, len(data_sorted) + 1) / len(data_sorted)
    
    return data_sorted, cdf

def plot_cdf(data, title='CDF', xlabel='Value', ylabel='CDF', ax=None, **kwargs):
    """
    Plots the Cumulative Distribution Function (CDF) of a data array.

    Parameters:
    data (array-like): The data array for which the CDF is to be plotted.
    title (str): The title of the plot.
    xlabel (str): The label for the x-axis.
    ylabel (str): The label for the y-axis.
    """
    # Get the CDF values
    data_sorted, cdf = get_cdf(data)
    
    # Plot the CDF
    if ax is None:
        plt.figure(figsize=(8, 5))
        ax = plt.gca()

    presets = {
        'marker': 'o',
        'markersize': 1,
        'linestyle': '-',
        'linewidth': 1,
        'color': 'black'
    }
    presets.update(kwargs)

    ax.plot(data_sorted, cdf, **presets)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.grid(True)

# Example usage
if __name__ == '__main__':
    data = np.random.randn(1000)  # Generate some random data
    plot_cdf(data, title='CDF of Random Data', xlabel='Data Value', ylabel='CDF')
    plt.show()