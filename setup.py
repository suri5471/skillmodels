from setuptools import find_packages
from setuptools import setup

setup(
    name="skillmodels",
    version="0.0.62",
    packages=find_packages() + ["skillmodels.tests"],
    package_data={"skillmodels": ["visualization/preamble.tex"]},
    include_package_data=True,
)
