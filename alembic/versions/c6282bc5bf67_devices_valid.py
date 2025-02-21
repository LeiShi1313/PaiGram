"""devices_valid

Revision ID: c6282bc5bf67
Revises: 1df05b897d3f
Create Date: 2023-10-19 14:54:35.164497

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c6282bc5bf67"
down_revision = "1df05b897d3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("devices", sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="1"))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("devices", "is_valid")
    # ### end Alembic commands ###
