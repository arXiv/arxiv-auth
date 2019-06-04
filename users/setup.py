"""Install arXiv auth package."""

from setuptools import setup, find_packages

setup(
    name='arxiv-auth',
    version='0.3.2rc8',
    packages=[f'arxiv.{package}' for package
              in find_packages('./arxiv', exclude=['*test*'])],
    install_requires=[
        "pycountry",
        "sqlalchemy",
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
