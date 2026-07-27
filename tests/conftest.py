import os

import pytest
from werkzeug.security import generate_password_hash


os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_PASSWORD_HASH"] = generate_password_hash("test-password")
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["TMDB_API_KEY"] = "test-tmdb-key"


@pytest.fixture
def app():
    from api.index import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app
