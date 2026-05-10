import os
import pytest
from backend.app import create_app
from backend.app.db import get_db

@pytest.fixture
def app():
    # Set testing config
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    app.config.update({
        "TESTING": True,
        "JWT_SECRET_KEY": "test-jwt-secret"
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Log in as super admin to get JWT token for tests."""
    response = client.post('/api/auth/login', json={
        "email": "admin@hospify.com",
        "password": "Password123!"
    })
    
    if response.status_code != 200:
        pytest.skip("Test database not seeded. Please run seed_data.py first.")
        
    access_token = None
    for cookie in response.headers.getlist('Set-Cookie'):
        if 'access_token_cookie' in cookie:
            access_token = cookie.split(';')[0].split('=')[1]
            break
            
    return {"Cookie": f"access_token_cookie={access_token}"}

def test_health_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok"}

def test_get_patients(client, auth_headers):
    response = client.get('/api/patients/', headers=auth_headers)
    assert response.status_code == 200
    assert type(response.json) == list

def test_get_active_admissions(client, auth_headers):
    response = client.get('/api/admissions/', headers=auth_headers)
    assert response.status_code == 200
    assert type(response.json) == list
