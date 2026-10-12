from alembic import context

from app.db import engine
from app.models import Base


def include_object(obj, name, type_, reflected, compare_to):
    # Never treat PostGIS extension-owned tables as application migration objects.
    return not (type_ == "table" and reflected and name not in Base.metadata.tables)


with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=Base.metadata, include_object=include_object
    )
    with context.begin_transaction():
        context.run_migrations()
