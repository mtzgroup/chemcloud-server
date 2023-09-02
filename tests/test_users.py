def test_login_redirects_to_auth0_server(client, settings):
    response = client.get(f"{settings.users_prefix}/login", follow_redirects=False)
    assert response.status_code == 307
    # Will be redirecting back to a route intended for Auth0 callback
    assert "/api/v1/oauth/auth0/callback" in response.headers["location"]


def test_dashboard_redirects_to_login_without_cookie_auth(client, settings):
    response = client.get(f"{settings.users_prefix}/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == f"{settings.users_prefix}/login"


def test_dashboard_redirects_to_login_with_invalid_cookie_auth(client, settings):
    response = client.get(f"{settings.users_prefix}/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == f"{settings.users_prefix}/login"
