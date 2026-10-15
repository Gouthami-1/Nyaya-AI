import os
import tempfile
import pytest
from app import app as flask_app

@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, DATABASE_PATH=path, STORE_HISTORY=False)
    with flask_app.test_client() as client:
        yield client
    os.unlink(path)

def test_home_page(client):
    response=client.get('/')
    assert response.status_code == 200
    assert b'Nyaya AI' in response.data

def test_empty_question_rejected(client):
    response=client.post('/api/chat', json={'message':'  '})
    assert response.status_code == 400
