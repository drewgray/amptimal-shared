"""Shared auth utilities for FastAPI services.

Provides reusable FastAPI dependencies that extract user identity and enforce
role/permission checks using headers set by the Traefik forwardAuth middleware.

The auth service's /verify endpoint decodes the JWT and sets:
- X-User-Id: authenticated user's ID
- X-User-Email: authenticated user's email
- X-User-Roles: comma-separated list of roles

These dependencies read those headers and provide authorization enforcement.

Usage::

    from amptimal_shared.auth import get_current_user, require_role, require_permission

    @app.get("/admin-only")
    async def admin_endpoint(user=Depends(require_role("admin"))):
        return {"user": user.user_id}

    @app.get("/data")
    async def data_endpoint(user=Depends(require_permission("data:read"))):
        return {"user": user.user_id}

    @app.get("/profile")
    async def profile(user=Depends(get_current_user)):
        return {"user_id": user.user_id, "email": user.email}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Lazy import of contracts to avoid hard dependency.
# If amptimal-contracts is not installed, permission resolution falls back
# to an empty mapping (role checks still work, permission checks require contracts).
_ROLE_PERMISSIONS: dict | None = None
_contracts_loaded = False


def _load_contracts() -> dict:
    """Lazily load the ROLE_PERMISSIONS mapping from amptimal-contracts."""
    global _ROLE_PERMISSIONS, _contracts_loaded
    if _contracts_loaded:
        return _ROLE_PERMISSIONS or {}
    _contracts_loaded = True
    try:
        from domains.auth.roles import ROLE_PERMISSIONS

        _ROLE_PERMISSIONS = {role.value: {p.value for p in perms} for role, perms in ROLE_PERMISSIONS.items()}
        logger.debug("Loaded ROLE_PERMISSIONS from amptimal-contracts")
    except ImportError:
        logger.warning(
            "amptimal-contracts not installed; permission resolution unavailable. "
            "Role-based checks will still work."
        )
        _ROLE_PERMISSIONS = {}
    return _ROLE_PERMISSIONS


@dataclass
class RequestUser:
    """Represents the authenticated user extracted from Traefik forwardAuth headers.

    Attributes:
        user_id: The unique user identifier from X-User-Id header.
        email: The user's email from X-User-Email header.
        roles: List of role strings from X-User-Roles header.
    """

    user_id: str
    email: str
    roles: list[str] = field(default_factory=list)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if any of the user's roles grant the given permission.

        Admin role always has all permissions. For other roles, the permission
        is resolved via the ROLE_PERMISSIONS mapping from amptimal-contracts.
        """
        if "admin" in self.roles:
            return True
        role_perms = _load_contracts()
        for role in self.roles:
            if permission in role_perms.get(role, set()):
                return True
        return False


def get_current_user(request: Request) -> RequestUser:
    """FastAPI dependency: extract authenticated user from forwardAuth headers.

    Reads X-User-Id, X-User-Email, and X-User-Roles headers set by the
    auth service's /verify endpoint via Traefik forwardAuth.

    Raises:
        HTTPException(401): If X-User-Id header is missing or empty.

    Returns:
        RequestUser with the authenticated user's identity.
    """
    user_id = request.headers.get("X-User-Id", "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = request.headers.get("X-User-Email", "").strip()
    roles_header = request.headers.get("X-User-Roles", "").strip()
    roles = [r.strip() for r in roles_header.split(",") if r.strip()] if roles_header else []

    return RequestUser(user_id=user_id, email=email, roles=roles)


def require_role(*required_roles: str) -> Callable:
    """FastAPI dependency factory: require the user to have one of the specified roles.

    Admin role always passes regardless of the required roles.

    Args:
        *required_roles: One or more role strings. User must have at least one.

    Returns:
        A FastAPI dependency function that returns RequestUser if authorized.

    Raises:
        HTTPException(401): If user is not authenticated.
        HTTPException(403): If user lacks the required role.

    Usage::

        @app.get("/traders", dependencies=[Depends(require_role("trader", "admin"))])
        async def traders_only():
            ...

        @app.get("/me")
        async def me(user=Depends(require_role("viewer"))):
            return {"user_id": user.user_id}
    """

    def dependency(request: Request) -> RequestUser:
        user = get_current_user(request)

        # Admin always passes
        if "admin" in user.roles:
            return user

        # Check if user has any of the required roles
        if not any(role in user.roles for role in required_roles):
            logger.warning(
                "Access denied: user=%s has roles=%s, required one of %s",
                user.user_id,
                user.roles,
                required_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )

        return user

    return dependency


def require_permission(*required_permissions: str) -> Callable:
    """FastAPI dependency factory: require specific permissions resolved from user roles.

    Permissions are resolved from roles via the ROLE_PERMISSIONS mapping defined
    in amptimal-contracts. Admin role always has all permissions.

    Args:
        *required_permissions: One or more permission strings (e.g., "data:read").
            User must have ALL specified permissions.

    Returns:
        A FastAPI dependency function that returns RequestUser if authorized.

    Raises:
        HTTPException(401): If user is not authenticated.
        HTTPException(403): If user lacks any of the required permissions.

    Usage::

        @app.get("/data")
        async def read_data(user=Depends(require_permission("data:read"))):
            ...

        @app.post("/trades")
        async def execute_trade(user=Depends(require_permission("trading:read", "trading:execute"))):
            ...
    """

    def dependency(request: Request) -> RequestUser:
        user = get_current_user(request)

        # Admin always passes
        if "admin" in user.roles:
            return user

        # Resolve permissions from roles
        role_perms = _load_contracts()
        user_permissions: set[str] = set()
        for role in user.roles:
            user_permissions.update(role_perms.get(role, set()))

        # Check that user has ALL required permissions
        missing = [p for p in required_permissions if p not in user_permissions]
        if missing:
            logger.warning(
                "Access denied: user=%s missing permissions=%s (has roles=%s)",
                user.user_id,
                missing,
                user.roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

        return user

    return dependency
