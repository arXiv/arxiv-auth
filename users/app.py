import sys
sys.path.append('./arxiv')

from flask import Flask
from users import authorization, legacy

app = Flask('test')
legacy.init_app(app)
legacy.create_all()
