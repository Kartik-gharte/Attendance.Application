from app.database.attendance_db import get_connection


def test_connection_creates_configured_parent_directory(tmp_path):

    database_path = tmp_path / "nested" / "attendance-test.db"

    connection = get_connection(database_path)

    try:
        assert database_path.exists()
    finally:
        connection.close()
