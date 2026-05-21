from sqlalchemy import text


def test_test_database_connection(db_session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_client_uses_test_app(client):
    response = client.get("/health")
    assert response.status_code == 200
