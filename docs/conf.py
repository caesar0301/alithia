# Configuration file for the Sphinx documentation builder.

project = 'mirasurf-py-template'
copyright = '2024, Mirasurf Team'
author = 'Mirasurf Team'
release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme' 