import unittest
import requests


class TestLogin(unittest.TestCase):
    def test_auth_get(self):
        response = requests.get('http://127.0.0.1:8080/auth/ntaiatarxiv')
        self.assertEqual(200, response.status_code)

    def test_auth_post(self):
        response = requests.post('http://127.0.0.1:8080/auth/ntaiatarxiv',
                                 json={"password": "nevada_37_elvish_handed_cocky"})
        self.assertEqual(200, response.status_code)


if __name__ == '__main__':
    unittest.main()
