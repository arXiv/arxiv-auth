"""Install arXiv mail package."""

from setuptools import setup, find_packages

setup(
    name='arxiv-mail',
    version='0.1.0',
    packages=[f'arxiv.{package}' for package
              in find_packages('./arxiv', exclude=['*test*'])],
    install_requires=[
    ],
    zip_safe=False
)
