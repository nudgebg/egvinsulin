from setuptools import setup, find_packages

# Read the README file for long_description
with open("docs/README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="babelbetes",  # The package name on pip install
    use_scm_version=True,
    description="A Data Processing Tool to Standardize Publicly Available Clinical Diabetes Trial Data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nudgebg/babelbetes",
    packages=find_packages(),
    license="MIT",
    python_requires=">=3, <4",
    install_requires=[
        "setuptools-scm",
        "numpy>=1.26.4,<2.0",
        "pandas>=2.2.2,<3.0",
        "pyarrow",
        "scipy>=1.13.0,<2.0",
        "matplotlib>=3.9.3,<4.0",
        "dask>=2024.8.0",
        "dask-expr>=1.1.10",
        "isodate>=0.7.2",
        "zipfile-deflate64-macos",
        "pandera==0.28.1",
        "squarify>=0.4.3",
        "tqdm",
    ],

    # Development/documentation dependencies
    extras_require={
        "notebook": [
            "ipykernel>=6.29.5",
            "ipywidgets>=8.1.5",
            "notebook>=7.2.2",
            "ipympl>=0.9.4",
            "bokeh>=3.4.3,<4.0",
            "graphviz>=0.20.3",
            "squarify>=0.4.3",
        ],
        "dev": [
            "pytest>=8.2.2",
            "mkdocs>=1.6.1",
            "mkdocs-material>=9.5.36",
            "mkdocstrings>=1.0",
            "mkdocstrings-python>=2.0",
            "pymdown-extensions>=10.8.1",
            "mike",
        ],
    },
    include_package_data=True,  # Include files from MANIFEST.in
)