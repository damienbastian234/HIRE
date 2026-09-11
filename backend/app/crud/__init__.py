"""CRUD repository layer for H.I.R.E. database models.

Exposes repositories for User, Profile, and Resume models alongside the
generic CRUDBase repository.
"""

from app.crud.base import CRUDBase
from app.crud.crud_profile import CRUDProfile, crud_profile
from app.crud.crud_resume import CRUDResume, crud_resume
from app.crud.crud_user import CRUDUser, crud_user

# Convenience aliases
user = crud_user
profile = crud_profile
resume = crud_resume

__all__ = [
    "CRUDBase",
    "CRUDUser",
    "crud_user",
    "user",
    "CRUDProfile",
    "crud_profile",
    "profile",
    "CRUDResume",
    "crud_resume",
    "resume",
]
