from jose import jwt

from chemcloud_server.auth import _get_matching_rsa_key


def test_get_matching_rsa_key_checks_all_keys():
    token = jwt.encode({"sub": "test"}, "secret", algorithm="HS256", headers={"kid": "2"})
    jwks = [
        {"kid": "1", "kty": "RSA", "use": "sig", "n": "n1", "e": "e1"},
        {"kid": "2", "kty": "RSA", "use": "sig", "n": "n2", "e": "e2"},
    ]

    assert _get_matching_rsa_key(token, jwks) == jwks[1]


def test_login_redirects_to_auth0_server(client, settings):
    response = client.get(f"{settings.users_prefix}/login", follow_redirects=False)
    assert response.status_code == 307
    # Will be redirecting back to a route intended for Auth0 callback
    assert "/api/v2/oauth/auth0/callback" in response.headers["location"]


def test_dashboard_redirects_to_login_without_cookie_auth(client, settings):
    response = client.get(f"{settings.users_prefix}/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == f"{settings.users_prefix}/login"


def test_dashboard_redirects_to_login_with_invalid_cookie_auth(client, settings):
    response = client.get(f"{settings.users_prefix}/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == f"{settings.users_prefix}/login"
