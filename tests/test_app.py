import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF tokens in tests
    with app.test_client() as client:
        yield client

@patch('mysql.connector.connect')
def test_home_page(mock_db, client):
    """Test that home page loads successfully"""
    # Configure the mock database connection
    mock_db.return_value.cursor.return_value.fetchall.return_value = []
    
    rv = client.get('/')
    assert rv.status_code == 200

def test_app_creation():
    """Test Flask app creation"""
    assert app is not None
