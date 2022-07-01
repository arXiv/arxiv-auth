import pytest

from arxiv.cloud_auth.userstore import UserStore, UserStoreDB


def test_userstore(userstore):
    user = userstore.getuser(-1)
    assert user is None

    ph = userstore.getuser(1)
    assert ph

    nobody = userstore.getuser_by_nick("fakename-should-not-be-in-user_db")
    assert nobody is None

    skunk = userstore.getuser_by_nick("skunk")
    assert skunk
    assert skunk.moderated_archives == []
    assert set(skunk.moderated_categories) == set(["bicycles.tall", "bicycles.chopped"])

    skunk2 = userstore.getuser(2)
    assert skunk == skunk2

    skunk3 = userstore.getuser_by_email("sk@s.org")
    assert skunk == skunk3

    assert userstore.invalidate_user(2)
    assert not userstore.invalidate_user(2)

    skunk4 = userstore.getuser(1)
    skunk4 == skunk

    no = userstore.getuser_by_nick("")
    no = userstore.getuser_by_email("")

    user = userstore.getuser_by_nick("金剛經")
    user.username == "金剛經"
