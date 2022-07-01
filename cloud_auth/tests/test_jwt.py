import arxiv.cloud_auth.jwt as jwt
from arxiv.cloud_auth.domain import Auth


def test_encode_decode():
    data = Auth(
        user_id="1234344", session_id="2342432", nonce="cheeseburger", expires="foo"
    )
    sec = "l2k3j4lkjlkdsj"
    assert jwt.decode(jwt.encode(data, sec), sec) == vars(data)
