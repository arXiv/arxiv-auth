"""Tests for :mod:`accounts.routes.ui`."""

from unittest import TestCase, mock
from arxiv import status
from accounts.factory import create_web_app


from flask_wtf.csrf import generate_csrf


# TODO: add mocking when the controllers get wired up.
class TestLoginLogoutRoutes(TestCase):
    """Test login and logout routes."""

    def setUp(self):
        """Initialize a test app and client."""
        self.app = create_web_app()

        # Disable CSRF protection for this request.
        self.app.config['WTF_CSRF_CHECK_DEFAULT'] = False
        self.app.config['WTF_CSRF_METHODS'] = []
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app.app_context().push()

    def test_get_login(self):
        """GET request to /login returns the login form."""
        response = self.client.get('/user/login')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')

    def test_post_login(self):
        """POST request to /login with valid form data returns redirect."""
        form_data = {'username': 'foo', 'password': 'bar'}
        response = self.client.post('/user/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)

    def test_post_login_baddata(self):
        """POST rquest to /login with invalid data returns 200."""
        response = self.client.post('/user/login', data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
