"""Flask configuration."""

import os

VERSION = '0.2'

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf1234')
SERVER_NAME = os.environ.get('ZERO_SERVER_NAME')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'nope')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'nope')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

LOGFILE = os.environ.get('LOGFILE')
LOGLEVEL = os.environ.get('LOGLEVEL', 20)

SQLALCHEMY_DATABASE_URI = os.environ.get('ZERO_SQLALCHEMY_DATABASE_URI',
                                         'sqlite:///accounts.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

JWT_SECRET = os.environ.get('JWT_SECRET', 'foosecret')
