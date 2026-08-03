import sys
from sqlalchemy import text
from app.database import engine

# Reconfigure stdout to handle UTF-8 symbols (e.g. checkmark) on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def test_connection():
    """
    Test PostgreSQL database connection using SQLAlchemy engine.
    Prints success message on clean connection, or exception message on failure.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ Database Connected Successfully")
    except Exception as e:
        print(f"Database Connection Failed: {e}")


if __name__ == "__main__":
    test_connection()
