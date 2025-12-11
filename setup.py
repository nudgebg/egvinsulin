from setuptools import setup, find_packages

# Read the README file for long_description
with open("docs/README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="babelbetes",  # The package name on pip install
    version="0.1.2",  # Update version as needed
    description="Extracting standardized tables from heterogeneous diabetes management datasets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nudgebg/babelbetes",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3, <4",
    install_requires=[
        "numpy==1.26.4",
        "pandas==2.2.2",
        "scipy==1.13.0",
        "pytest==8.2.2",
        "mkdocs==1.6.1",
        "mkdocs-material==9.5.36",
        "mkdocstrings-python==1.11.1",
        "pymdown-extensions==10.8.1",
        "tqdm==4.66.5",
        "mkdocs-with-pdf==0.9.3",
        "ipykernel>=6.29.5",
        "matplotlib==3.9.3",
        "ipywidgets==8.1.5",
        "notebook==7.2.2",
        "ipympl==0.9.4",
        "bokeh==3.4.3",
        "graphviz==0.20.3",
        "dask==2024.8.0",
        "dask-expr==1.1.10",
        "isodate==0.7.2",
        "zipfile_deflate64"
    ],
    include_package_data=True,  # Include files from MANIFEST.in
)