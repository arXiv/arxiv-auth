"""Install arXiv auth package."""

from setuptools import setup, find_packages

setup(
    name='arxiv-auth',
    version='0.4.2',
    packages=[f'arxiv.{package}' for package
              in find_packages('./arxiv', exclude=['*test*'])],
    scripts=['bin/generate-token'],
    install_requires=[
        "pycountry",
        "sqlalchemy",
        "mimesis",
        "mysqlclient",
        "python-dateutil",
        "arxiv-base",
        "pyjwt",
        "redis==2.10.6",
        "redis-py-cluster==1.3.6",
        "flask-sqlalchemy"
    ],
    zip_safe=False
)
