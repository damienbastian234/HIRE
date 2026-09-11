"""create_skill_table

Revision ID: 767028913f6e
Revises: 729e24449128
Create Date: 2026-09-11 10:47:00.077444

Migration creating the skill table according to H.I.R.E. database specifications:
- skill (extracted candidate skills, foreign key to resume, confidence score)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "767028913f6e"
down_revision: Union[str, Sequence[str], None] = "729e24449128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create skill table, foreign key, and resume_id index."""
    op.create_table(
        "skill",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("skill_category", sa.String(length=100), nullable=True),
        sa.Column("confidence_score", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resume.id"],
            name=op.f("fk_skill_resume_id_resume"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill")),
    )
    op.create_index(op.f("ix_skill_resume_id"), "skill", ["resume_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop skill table and its index."""
    op.drop_index(op.f("ix_skill_resume_id"), table_name="skill")
    op.drop_table("skill")
