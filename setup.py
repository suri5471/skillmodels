from setuptools import setup, find_packages

setup(
    name='skillmodels',
    version='0.0.51',
    packages=find_packages(),
    package_data={'skillmodels': ['visualization/preamble.tex']},
    include_package_data=True
)
