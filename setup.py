# Automatically created by: shub deploy

from setuptools import setup, find_packages

setup(
    name         = 'pnas',
    version      = '1.0',
    packages     = find_packages(),
    package_data = {'pnas': ['resources/*.csv']},
    entry_points = {'scrapy': ['settings = pnas.settings']},
)
