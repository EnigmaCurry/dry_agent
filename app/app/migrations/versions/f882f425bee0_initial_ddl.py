"""initial DDL

Revision ID: f882f425bee0
Revises: 
Create Date: 2025-04-30 16:45:40.974138

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision: str = "f882f425bee0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using raw SQL file."""
    current_dir = os.path.dirname(os.path.realpath(__file__))
    sql_file_path = os.path.join(current_dir, f"{revision}_initial_ddl.sql")

    with open(sql_file_path, "r") as file:
        sql_commands = file.read()

    # Split statements on semicolon followed by optional whitespace and a newline.
    statements = [s.strip() for s in sql_commands.split(";") if s.strip()]

    # Execute each statement one-by-one.
    conn = op.get_bind()
    for stmt in statements:
        conn.execute(sa.text(stmt))


def downgrade() -> None:
    """Downgrade schema."""
    pass
