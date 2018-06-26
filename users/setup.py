"""Install arXiv auth package."""

from setuptools import setup, find_packages

setup(
    name='arxiv-users',
    version='0.1.1',
    packages=[f'arxiv.{package}' for package
              in find_packages('./arxiv', exclude=['*test*'])],
    zip_safe=False
)
