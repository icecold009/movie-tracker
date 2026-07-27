import os

from dotenv import load_dotenv


load_dotenv()


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SECRET_KEY = required_env("SECRET_KEY")
ADMIN_PASSWORD_HASH = required_env("ADMIN_PASSWORD_HASH")
if ADMIN_PASSWORD_HASH.count("$") < 2:
    raise RuntimeError(
        "ADMIN_PASSWORD_HASH must be a Werkzeug password hash, not plaintext"
    )
DATABASE_URL = required_env("DATABASE_URL")
TMDB_API_KEY = required_env("TMDB_API_KEY")
