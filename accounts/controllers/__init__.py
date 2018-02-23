"""Contains arxiv-accounts controller sketches."""

# TODO: these still need to be implemented; this is just enough to get the
# routes mapped out.


from typing import Dict, Tuple
from arxiv import status
from .forms import LoginForm


def get_login() -> Tuple[dict, int, dict]:
    """Get the login form."""
    return {'form': LoginForm()}, status.HTTP_200_OK, {}


def post_login(form_data: dict, ip_address: str) -> Tuple[dict, int, dict]:
    """Process submitted login form."""
    form = LoginForm(form_data)

    code = status.HTTP_200_OK
    if form.validate_on_submit():
        code = status.HTTP_303_SEE_OTHER

    data = {'form': form}
    # TODO: hook this up to session services.
    data['session_id'] = 'foo_session'
    data['tapir_session_id'] = 'tapir_foo_session'
    return data, code, {'Location': 'https://arxiv.org/user/'}


def logout(session_id: str) -> Tuple[dict, int, dict]:
    """Log the user out, and redirect to arXiv.org."""
    # TODO: implement session deletion here.
    return {}, status.HTTP_303_SEE_OTHER, {'Location': 'https://arxiv.org/'}
