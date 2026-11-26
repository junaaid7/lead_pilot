import pytest
from sqlalchemy.orm import Session

from app.db import engine


@pytest.fixture()
def session():
    connection = engine.connect()
    outer = connection.begin()  # bahar ka transaction, test ke end par rollback hoga
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    yield session
    session.close()
    outer.rollback()  # test ne jo bhi likha tha sab wapas, database saaf rehta hai
    connection.close()