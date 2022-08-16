"""test app."""

import sys
sys.path.append('./arxiv')

from flask import Flask
from arxiv_users import auth, legacy

app = Flask('test')
legacy.init_app(app)
legacy.create_all()
