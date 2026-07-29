"""RBAC dependency. Role check (Admin / Finance Staff / Viewer) enforced at
the API layer on every state-changing endpoint; Viewer is read-only across
the board.
"""

from collections.abc import Callable

from fastapi import Depends

from app.api.deps import get_current_user
from app.core.exceptions import AuthorizationError
from app.models.user import User, UserRole


def require_role(*roles: UserRole) -> Callable[..., User]:
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AuthorizationError(
                f"Role '{user.role.value}' is not permitted to perform this action"
            )
        return user

    return _dependency


require_admin = require_role(UserRole.admin)
require_staff = require_role(UserRole.admin, UserRole.finance_staff)
require_any_role = require_role(UserRole.admin, UserRole.finance_staff, UserRole.viewer)
