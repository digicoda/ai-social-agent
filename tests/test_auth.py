from app.auth import authenticate, create_admin, has_users


def test_first_admin_signup_and_login(tmp_path):
    database = f"sqlite:///{tmp_path / 'auth.db'}"

    assert not has_users(database)
    assert create_admin(database, "myadmin", "correct-horse-battery")
    assert has_users(database)
    assert not create_admin(database, "second", "another-password")
    assert authenticate(database, "myadmin", "correct-horse-battery")
    assert authenticate(database, "MYADMIN", "correct-horse-battery")
    assert not authenticate(database, "myadmin", "wrong-password")
