"""Tests for shared auth utilities (FastAPI dependencies)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from amptimal_shared.auth import (
    RequestUser,
    get_current_user,
    require_permission,
    require_role,
)


@pytest.fixture(autouse=True)
def reset_contracts_cache():
    """Reset the lazy-loaded contracts cache between tests."""
    import amptimal_shared.auth as mod

    mod._ROLE_PERMISSIONS = None
    mod._contracts_loaded = False
    yield
    mod._ROLE_PERMISSIONS = None
    mod._contracts_loaded = False


def _make_request(
    user_id: str = "",
    email: str = "",
    roles: str = "",
) -> MagicMock:
    """Create a mock FastAPI Request with X-User-* headers."""
    request = MagicMock()
    headers = {
        "X-User-Id": user_id,
        "X-User-Email": email,
        "X-User-Roles": roles,
    }
    request.headers.get = lambda key, default="": headers.get(key, default)
    return request


class TestRequestUser:
    """Tests for the RequestUser dataclass."""

    def test_basic_creation(self):
        """Should create a RequestUser with all fields."""
        user = RequestUser(user_id="user-1", email="user@test.com", roles=["admin"])
        assert user.user_id == "user-1"
        assert user.email == "user@test.com"
        assert user.roles == ["admin"]

    def test_default_roles(self):
        """Should default to empty roles list."""
        user = RequestUser(user_id="user-1", email="user@test.com")
        assert user.roles == []

    def test_has_role_true(self):
        """Should return True when user has the role."""
        user = RequestUser(user_id="user-1", email="u@t.com", roles=["trader", "viewer"])
        assert user.has_role("trader") is True

    def test_has_role_false(self):
        """Should return False when user lacks the role."""
        user = RequestUser(user_id="user-1", email="u@t.com", roles=["viewer"])
        assert user.has_role("admin") is False

    def test_has_permission_admin_always_true(self):
        """Admin role should always have any permission."""
        user = RequestUser(user_id="admin-1", email="a@t.com", roles=["admin"])
        assert user.has_permission("data:read") is True
        assert user.has_permission("admin:system") is True
        assert user.has_permission("nonexistent:perm") is True

    def test_has_permission_with_contracts(self):
        """Should resolve permission from ROLE_PERMISSIONS mapping."""
        import amptimal_shared.auth as mod

        # Simulate loaded contracts
        mod._contracts_loaded = True
        mod._ROLE_PERMISSIONS = {
            "trader": {"data:read", "trading:execute"},
            "viewer": {"data:read"},
        }

        user = RequestUser(user_id="user-1", email="u@t.com", roles=["trader"])
        assert user.has_permission("data:read") is True
        assert user.has_permission("trading:execute") is True
        assert user.has_permission("admin:system") is False

    def test_has_permission_without_contracts(self):
        """Should return False when contracts not installed and not admin."""
        import amptimal_shared.auth as mod

        mod._contracts_loaded = True
        mod._ROLE_PERMISSIONS = {}

        user = RequestUser(user_id="user-1", email="u@t.com", roles=["trader"])
        assert user.has_permission("data:read") is False


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_extracts_user_from_headers(self):
        """Should extract user identity from X-User-* headers."""
        request = _make_request(
            user_id="user-123",
            email="user@amptimal.com",
            roles="trader,analyst",
        )
        user = get_current_user(request)
        assert user.user_id == "user-123"
        assert user.email == "user@amptimal.com"
        assert user.roles == ["trader", "analyst"]

    def test_single_role(self):
        """Should handle a single role without commas."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="admin")
        user = get_current_user(request)
        assert user.roles == ["admin"]

    def test_empty_roles(self):
        """Should handle empty roles header."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="")
        user = get_current_user(request)
        assert user.roles == []

    def test_strips_whitespace_from_roles(self):
        """Should strip whitespace from individual roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles=" trader , analyst ")
        user = get_current_user(request)
        assert user.roles == ["trader", "analyst"]

    def test_strips_whitespace_from_user_id(self):
        """Should strip whitespace from user_id."""
        request = _make_request(user_id="  user-1  ", email="u@t.com")
        user = get_current_user(request)
        assert user.user_id == "user-1"

    def test_strips_whitespace_from_email(self):
        """Should strip whitespace from email."""
        request = _make_request(user_id="user-1", email="  u@t.com  ")
        user = get_current_user(request)
        assert user.email == "u@t.com"

    def test_raises_401_when_no_user_id(self):
        """Should raise 401 when X-User-Id header is missing."""
        request = _make_request(user_id="", email="u@t.com")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    def test_raises_401_when_user_id_is_whitespace(self):
        """Should raise 401 when X-User-Id is whitespace only."""
        request = _make_request(user_id="   ", email="u@t.com")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_no_headers_raises_401(self):
        """Should raise 401 when no user headers are set."""
        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_filters_empty_role_segments(self):
        """Should filter out empty segments from roles like 'trader,,analyst'."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="trader,,analyst")
        user = get_current_user(request)
        assert user.roles == ["trader", "analyst"]


class TestRequireRole:
    """Tests for require_role dependency factory."""

    def test_allows_matching_role(self):
        """Should allow access when user has the required role."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="trader")
        dep = require_role("trader")
        user = dep(request)
        assert user.user_id == "user-1"
        assert user.roles == ["trader"]

    def test_allows_one_of_multiple_roles(self):
        """Should allow access when user has any one of the required roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="analyst")
        dep = require_role("trader", "analyst")
        user = dep(request)
        assert user.user_id == "user-1"

    def test_blocks_non_matching_role(self):
        """Should deny access when user has none of the required roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="viewer")
        dep = require_role("trader", "analyst")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Insufficient role"

    def test_admin_bypass(self):
        """Admin role should always pass regardless of required roles."""
        request = _make_request(user_id="admin-1", email="a@t.com", roles="admin")
        dep = require_role("trader")
        user = dep(request)
        assert user.user_id == "admin-1"

    def test_admin_in_mixed_roles_bypasses(self):
        """Admin should bypass even when mixed with other roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="viewer,admin")
        dep = require_role("trader")
        user = dep(request)
        assert user.user_id == "user-1"

    def test_raises_401_when_not_authenticated(self):
        """Should raise 401 when user is not authenticated."""
        request = _make_request(user_id="", email="")
        dep = require_role("trader")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 401

    def test_empty_roles_denied(self):
        """Should deny access when user has no roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="")
        dep = require_role("trader")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 403


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    @pytest.fixture(autouse=True)
    def setup_role_permissions(self):
        """Set up a mock ROLE_PERMISSIONS mapping for permission tests."""
        import amptimal_shared.auth as mod

        mod._contracts_loaded = True
        mod._ROLE_PERMISSIONS = {
            "trader": {"data:read", "trading:read", "trading:execute", "risk:read", "ml:read", "finance:read", "notifications:manage"},
            "analyst": {"data:read", "data:write", "ml:read", "ml:train", "risk:read", "finance:read", "compliance:read"},
            "viewer": {"data:read", "trading:read", "risk:read", "ml:read", "finance:read", "compliance:read"},
            "service": {"data:read", "data:write", "ml:read", "trading:read"},
        }
        yield

    def test_allows_matching_permission(self):
        """Should allow access when user has the required permission."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="trader")
        dep = require_permission("data:read")
        user = dep(request)
        assert user.user_id == "user-1"

    def test_allows_multiple_permissions(self):
        """Should allow access when user has all required permissions."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="trader")
        dep = require_permission("trading:read", "trading:execute")
        user = dep(request)
        assert user.user_id == "user-1"

    def test_blocks_missing_permission(self):
        """Should deny access when user lacks a required permission."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="viewer")
        dep = require_permission("trading:execute")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 403
        assert "trading:execute" in exc_info.value.detail

    def test_blocks_partial_permission_match(self):
        """Should deny when user has some but not all required permissions."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="viewer")
        dep = require_permission("data:read", "data:write")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 403
        assert "data:write" in exc_info.value.detail

    def test_admin_bypass(self):
        """Admin role should always pass regardless of required permissions."""
        request = _make_request(user_id="admin-1", email="a@t.com", roles="admin")
        dep = require_permission("admin:system", "admin:users")
        user = dep(request)
        assert user.user_id == "admin-1"

    def test_admin_bypass_even_for_unknown_permissions(self):
        """Admin should pass even for permissions not in the enum."""
        request = _make_request(user_id="admin-1", email="a@t.com", roles="admin")
        dep = require_permission("nonexistent:permission")
        user = dep(request)
        assert user.user_id == "admin-1"

    def test_raises_401_when_not_authenticated(self):
        """Should raise 401 when user is not authenticated."""
        request = _make_request(user_id="", email="")
        dep = require_permission("data:read")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 401

    def test_combines_permissions_from_multiple_roles(self):
        """Should combine permissions from all user roles."""
        request = _make_request(user_id="user-1", email="u@t.com", roles="trader,analyst")
        # trader has trading:execute, analyst has ml:train
        dep = require_permission("trading:execute", "ml:train")
        user = dep(request)
        assert user.user_id == "user-1"

    def test_service_role_permissions(self):
        """Service role should have its designated permissions."""
        request = _make_request(user_id="svc-1", email="svc@t.com", roles="service")
        dep = require_permission("data:read", "data:write")
        user = dep(request)
        assert user.user_id == "svc-1"

    def test_service_role_lacks_admin(self):
        """Service role should not have admin permissions."""
        request = _make_request(user_id="svc-1", email="svc@t.com", roles="service")
        dep = require_permission("admin:users")
        with pytest.raises(HTTPException) as exc_info:
            dep(request)
        assert exc_info.value.status_code == 403


class TestContractsLazyLoading:
    """Tests for lazy loading of amptimal-contracts ROLE_PERMISSIONS."""

    def test_loads_contracts_on_first_permission_check(self):
        """Should attempt to import contracts on first permission check."""
        import amptimal_shared.auth as mod

        mod._contracts_loaded = False
        mod._ROLE_PERMISSIONS = None

        # Mock the import to simulate contracts being available
        with patch("amptimal_shared.auth._load_contracts") as mock_load:
            mock_load.return_value = {"trader": {"data:read"}}

            request = _make_request(user_id="user-1", email="u@t.com", roles="trader")
            dep = require_permission("data:read")
            dep(request)

            mock_load.assert_called()

    def test_graceful_when_contracts_not_installed(self):
        """Should not crash when amptimal-contracts is not installed."""
        import amptimal_shared.auth as mod

        mod._contracts_loaded = False
        mod._ROLE_PERMISSIONS = None

        # Simulate contracts not being importable
        with patch.dict("sys.modules", {"domains": None, "domains.auth": None, "domains.auth.roles": None}):
            mod._contracts_loaded = False
            mod._ROLE_PERMISSIONS = None

            # Force reload
            result = mod._load_contracts()
            assert isinstance(result, dict)

    def test_caches_after_first_load(self):
        """Should only load contracts once."""
        import amptimal_shared.auth as mod

        mod._contracts_loaded = True
        mod._ROLE_PERMISSIONS = {"trader": {"data:read"}}

        # Should use cached value without re-importing
        result = mod._load_contracts()
        assert result == {"trader": {"data:read"}}
