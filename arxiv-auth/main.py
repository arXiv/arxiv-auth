"""Provides application for development purposes."""
from accounts.factory import create_web_app

app = create_web_app()
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True

if __name__ == "__main__":
    app.run(debug=True)

