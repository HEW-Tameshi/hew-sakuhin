from sqlalchemy import text


def test_test_database_connection(test_engine):
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

    assert database_name == "kokoro_mail_test"
