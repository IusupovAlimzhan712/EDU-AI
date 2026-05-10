"""Sanity tests for the Account module (Week 2 deliverable)."""


def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


def test_register_success(client):
    r = client.post('/api/auth/register', json={
        'email': 'alice@example.com',
        'password': 'SecurePass1',
        'fullName': 'Alice Tan',
        'formLevel': 4,
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data['student']['email'] == 'alice@example.com'
    assert data['student']['formLevel'] == 4
    assert 'accessToken' in data
    assert 'refreshToken' in data


def test_register_duplicate_email(client):
    body = {
        'email': 'bob@example.com',
        'password': 'SecurePass1',
        'fullName': 'Bob Lim',
        'formLevel': 5,
    }
    assert client.post('/api/auth/register', json=body).status_code == 201
    r = client.post('/api/auth/register', json=body)
    assert r.status_code == 409


def test_register_weak_password(client):
    r = client.post('/api/auth/register', json={
        'email': 'weak@example.com',
        'password': 'weak',
        'fullName': 'Weak User',
        'formLevel': 4,
    })
    assert r.status_code == 422


def test_login_success(client):
    body = {
        'email': 'carol@example.com',
        'password': 'SecurePass1',
        'fullName': 'Carol Lee',
        'formLevel': 4,
    }
    client.post('/api/auth/register', json=body)
    r = client.post('/api/auth/login', json={
        'email': 'carol@example.com',
        'password': 'SecurePass1',
    })
    assert r.status_code == 200
    assert 'accessToken' in r.get_json()


def test_login_wrong_password(client):
    body = {
        'email': 'dave@example.com',
        'password': 'SecurePass1',
        'fullName': 'Dave',
        'formLevel': 5,
    }
    client.post('/api/auth/register', json=body)
    r = client.post('/api/auth/login', json={
        'email': 'dave@example.com',
        'password': 'WrongPass1',
    })
    assert r.status_code == 401


def test_me_endpoint_requires_auth(client):
    r = client.get('/api/me')
    assert r.status_code == 401


def test_me_endpoint_with_token(client):
    reg = client.post('/api/auth/register', json={
        'email': 'eve@example.com',
        'password': 'SecurePass1',
        'fullName': 'Eve',
        'formLevel': 5,
    }).get_json()
    token = reg['accessToken']
    r = client.get('/api/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    assert r.get_json()['email'] == 'eve@example.com'


def test_logout_invalidates_session(client):
    reg = client.post('/api/auth/register', json={
        'email': 'fred@example.com',
        'password': 'SecurePass1',
        'fullName': 'Fred',
        'formLevel': 4,
    }).get_json()
    token = reg['accessToken']
    auth = {'Authorization': f'Bearer {token}'}
    assert client.post('/api/auth/logout', headers=auth).status_code == 200
    # Now the same token should be rejected.
    assert client.get('/api/me', headers=auth).status_code == 401


def test_password_reset_flow(client):
    client.post('/api/auth/register', json={
        'email': 'grace@example.com',
        'password': 'OldPass1A',
        'fullName': 'Grace',
        'formLevel': 4,
    })
    r = client.post('/api/auth/forgot-password', json={'email': 'grace@example.com'})
    assert r.status_code == 200
    token = r.get_json().get('devResetToken')
    assert token, 'DEV_RETURN_RESET_TOKEN should expose the token'

    r = client.post('/api/auth/reset-password', json={
        'token': token,
        'newPassword': 'NewPass1A',
    })
    assert r.status_code == 200

    # Old password no longer works
    assert client.post('/api/auth/login', json={
        'email': 'grace@example.com',
        'password': 'OldPass1A',
    }).status_code == 401

    # New password works
    assert client.post('/api/auth/login', json={
        'email': 'grace@example.com',
        'password': 'NewPass1A',
    }).status_code == 200
