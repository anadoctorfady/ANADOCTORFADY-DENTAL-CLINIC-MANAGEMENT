"""Auth: default fady/1234."""
from src.models.database import init_db
from src.utils.auth import verify, hash_pw
def test_default_login():
    init_db()
    assert verify("fady", "1234") is True
    assert verify("fady", "wrong") is False
    assert verify("nope", "1234") is False
def test_hash():
    assert hash_pw("1234") == hash_pw("1234")
    assert hash_pw("1234") != hash_pw("1235")
