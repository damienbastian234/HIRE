"""create_user_profile_resume_tables

Revision ID: 729e24449128
Revises: 
Create Date: 2026-09-10 19:55:38.044047

Initial database migration for H.I.R.E. creating:
- user (authentication, credentials, roles, timestamps)
- profile (candidate personal, academic, and career information)
- resume (uploaded resume files, storage paths, parsing status)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "729e24449128"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create user, profile, and resume tables."""
    # 1. Create 'user' table
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
        sa.UniqueConstraint("email", name=op.f("uq_user_email")),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_created_at"), "user", ["created_at"], unique=False)

    # 2. Create 'profile' table
    op.create_table(
        "profile",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("college", sa.String(length=255), nullable=True),
        sa.Column("degree", sa.String(length=100), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("career_goal", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_profile_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile")),
        sa.UniqueConstraint("user_id", name=op.f("uq_profile_user_id")),
    )
    op.create_index(op.f("ix_profile_user_id"), "profile", ["user_id"], unique=True)

    # 3. Create 'resume' table
    op.create_table(
        "resume",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("parsing_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_resume_user_id_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resume")),
    )
    op.create_index(op.f("ix_resume_user_id"), "resume", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop resume, profile, and user tables in reverse order."""
    # 1. Drop 'resume' table
    op.drop_index(op.f("ix_resume_user_id"), table_name="resume")
    op.drop_table("resume")

    # 2. Drop 'profile' table
    op.drop_index(op.f("ix_profile_user_id"), table_name="profile")
    op.drop_table("profile")

    # 3. Drop 'user' table
    op.drop_index(op.f("ix_user_created_at"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
