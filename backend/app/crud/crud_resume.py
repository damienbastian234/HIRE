"""CRUD repository for Resume model.

Manages candidate resume records, upload metadata, status tracking, and deletion.
"""

from __future__ import annotations

from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.resume import Resume


class CRUDResume(CRUDBase[Resume]):
    """Repository managing Resume entity persistence and status transitions."""

    def __init__(self) -> None:
        """Initialize repository bound to the Resume model."""
        super().__init__(Resume)

    def create(
        self,
        db: Session,
        user_id: uuid.UUID,
        file_name: str,
        file_path: str,
        parsing_status: str = "pending",
    ) -> Resume:
        """Create and persist a new Resume record for a user.

        Args:
            db: Active database session.
            user_id: Owner user UUID.
            file_name: Original uploaded filename.
            file_path: Storage path or URI of the saved file.
            parsing_status: Pipeline parsing status (defaults to 'pending').

        Returns:
            The newly persisted and refreshed Resume instance.
        """
        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            parsing_status=parsing_status,
        )
        db.add(resume)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(resume)
        return resume

    def get_by_id(self, db: Session, resume_id: uuid.UUID) -> Optional[Resume]:
        """Retrieve a resume by its UUID primary key.

        Args:
            db: Active database session.
            resume_id: Resume UUID.

        Returns:
            The Resume instance if found, or None.
        """
        stmt = select(Resume).where(Resume.id == resume_id)
        return db.scalars(stmt).first()

    def list_by_user_id(self, db: Session, user_id: uuid.UUID) -> List[Resume]:
        """List all resumes belonging strictly to a specific user.

        Orders by upload_date in descending order (most recent first).

        Args:
            db: Active database session.
            user_id: Target user UUID.

        Returns:
            List of resumes belonging to the user.
        """
        stmt = (
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.upload_date.desc())
        )
        return list(db.scalars(stmt).all())

    def update_status(
        self,
        db: Session,
        resume_id: uuid.UUID,
        status: str,
    ) -> Optional[Resume]:
        """Update the parsing/processing status of a resume.

        Args:
            db: Active database session.
            resume_id: Resume UUID.
            status: New parsing status (e.g. 'processing', 'completed', 'failed').

        Returns:
            The updated Resume instance, or None if the resume was not found.
        """
        resume = self.get_by_id(db, resume_id=resume_id)
        if resume is None:
            return None

        resume.parsing_status = status
        db.add(resume)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(resume)
        return resume

    def delete(
        self,
        db: Session,
        resume_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Delete a resume record by ID, optionally validating owner user ID.

        If user_id is provided, deletion will only proceed if the resume
        belongs to that user, preventing cross-tenant accidental deletion.

        Args:
            db: Active database session.
            resume_id: Resume UUID to delete.
            user_id: Optional user UUID to verify ownership.

        Returns:
            True if the record was deleted, False if it was not found or
            ownership verification failed.
        """
        resume = self.get_by_id(db, resume_id=resume_id)
        if resume is None:
            return False

        # Guard against cross-user deletion if user_id is provided
        if user_id is not None and resume.user_id != user_id:
            return False

        db.delete(resume)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        return True


crud_resume = CRUDResume()
