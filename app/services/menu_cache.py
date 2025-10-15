from __future__ import annotations

import json
from dataclasses import dataclass, field
import os
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List, Optional, Set

CACHE_PATH = Path(__file__).resolve().parent.parent / "static" / "masters" / "menu_cache.json"
SYS_ADMIN_EMAILS = os.getenv("SYS_ADMIN_EMAILS", "").split(",")
SUPER_ADMIN_EMAILS = os.getenv("SUPER_ADMIN_EMAILS", "").split(",")

@dataclass
class MenuNode:
    id: int
    name: str
    url: str
    icon: Optional[str]
    order_index: int
    parent_id: Optional[int]
    is_active: bool
    children: List["MenuNode"] = field(default_factory=list)
    parent: Optional["MenuNode"] = None


_lock = RLock()
_cache_payload: Optional[Dict[str, object]] = None
_menu_index: Dict[int, Dict[str, object]] = {}
_role_menu_index: Dict[int, Set[int]] = {}
_default_role_id: Optional[int] = None
_anonymous_role_id: Optional[int] = None
_admin_role_id: Optional[int] = None
_super_admin_role_id: Optional[int] = None
_sys_admin_role_id: Optional[int] = None
_super_admin_emails: Set[str] = set()
_sys_admin_emails: Set[str] = set()
_cache_mtime: Optional[float] = None


def ensure_menu_cache() -> None:
    """Ensure the menu cache file exists by bootstrapping from DB if necessary."""
    with _lock:
        if CACHE_PATH.exists():
            _load_cache_locked()
            return
        refresh_menu_cache()


def refresh_menu_cache() -> None:
    """Rebuild the cache JSON from the current database state."""
    global _cache_payload, _cache_mtime
    from app.db import db
    from app.models.role import Role
    from app.models.menu_item import MenuItem
    from app.models.menu_in_role import MenuInRole

    with _lock:
        existing_overrides = {
            "super_admin_emails": SUPER_ADMIN_EMAILS,
            "sys_admin_emails": SYS_ADMIN_EMAILS,
        }
        if CACHE_PATH.exists():
            try:
                with CACHE_PATH.open("r", encoding="utf-8") as handle:
                    current = json.load(handle)
                overrides = current.get("overrides", {})
                if isinstance(overrides, dict):
                    existing_overrides["super_admin_emails"] = [
                        str(email).strip()
                        for email in overrides.get("super_admin_emails", [])
                        if str(email).strip()
                    ]
                    existing_overrides["sys_admin_emails"] = [
                        str(email).strip()
                        for email in overrides.get("sys_admin_emails", [])
                        if str(email).strip()
                    ]
            except (OSError, ValueError):
                pass

        roles = (
            db.session.query(Role)
            .order_by(Role.id)
            .all()
        )
        menu_items = (
            db.session.query(MenuItem)
            .order_by(MenuItem.order_index, MenuItem.id)
            .all()
        )
        menu_in_roles = (
            db.session.query(MenuInRole.role_id, MenuInRole.menu_id)
            .order_by(MenuInRole.role_id, MenuInRole.menu_id)
            .all()
        )

        payload = {
            "roles": [
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                }
                for role in roles
            ],
            "menu_items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "url": item.url,
                    "icon": item.icon,
                    "order_index": item.order_index,
                    "parent_id": item.parent_id,
                    "is_active": item.is_active,
                }
                for item in menu_items
            ],
            "menu_in_roles": [
                {"role_id": role_id, "menu_id": menu_id}
                for (role_id, menu_id) in menu_in_roles
            ],
            "overrides": existing_overrides,
        }

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

        _hydrate_from_payload(payload)
        _cache_payload = payload
        _cache_mtime = CACHE_PATH.stat().st_mtime


def get_roles() -> List[Dict[str, object]]:
    data = _load_cache()
    return list(data.get("roles", []))


def get_menu_items() -> List[Dict[str, object]]:
    data = _load_cache()
    return list(data.get("menu_items", []))


def get_role_ids_for_user(
    user_id: Optional[int],
    *,
    email: Optional[str] = None,
    is_admin: bool = False,
) -> Set[int]:
    _load_cache()
    resolved: Set[int] = set()

    if user_id is None:
        if _anonymous_role_id is not None:
            resolved.add(_anonymous_role_id)
        return resolved

    if _default_role_id is not None:
        resolved.add(_default_role_id)

    if is_admin and _admin_role_id is not None:
        resolved.add(_admin_role_id)

    normalized_email = (email or "").strip().lower()
    if normalized_email:
        if _super_admin_role_id is not None and normalized_email in _super_admin_emails:
            resolved.add(_super_admin_role_id)
        if _sys_admin_role_id is not None and normalized_email in _sys_admin_emails:
            resolved.add(_sys_admin_role_id)

    if not resolved and _default_role_id is not None:
        resolved.add(_default_role_id)

    return resolved


def get_menu_tree_for_roles(role_ids: Iterable[int]) -> List[MenuNode]:
    _load_cache()
    allowed_menu_ids: Set[int] = set()
    for rid in role_ids:
        allowed_menu_ids.update(_role_menu_index.get(int(rid), set()))
    if not allowed_menu_ids:
        return []

    expanded_ids = _include_parent_chain(allowed_menu_ids)
    nodes: Dict[int, MenuNode] = {}
    for menu_id in expanded_ids:
        record = _menu_index.get(menu_id)
        if not record or not record.get("is_active", True):
            continue
        nodes[menu_id] = MenuNode(
            id=record["id"],
            name=record["name"],
            url=record["url"],
            icon=record.get("icon"),
            order_index=record.get("order_index", 0),
            parent_id=record.get("parent_id"),
            is_active=record.get("is_active", True),
        )

    for node in nodes.values():
        parent_id = node.parent_id
        if parent_id and parent_id in nodes:
            parent = nodes[parent_id]
            node.parent = parent
            parent.children.append(node)

    def _sort_branch(branch: MenuNode) -> None:
        branch.children.sort(key=lambda child: (child.order_index, child.name.lower()))
        for child in branch.children:
            _sort_branch(child)

    top_level = [
        node for node in nodes.values()
        if not node.parent or node.parent.id not in nodes
    ]
    top_level.sort(key=lambda item: (item.order_index, item.name.lower()))
    for node in top_level:
        _sort_branch(node)
    return top_level


def get_flat_menu_for_roles(role_ids: Iterable[int]) -> List[MenuNode]:
    structured = get_menu_tree_for_roles(role_ids)
    flat: List[MenuNode] = []

    def _collect(node: MenuNode) -> None:
        flat.append(node)
        for child in node.children:
            _collect(child)

    for root in structured:
        _collect(root)
    return flat


def get_anonymous_role_id() -> Optional[int]:
    _load_cache()
    return _anonymous_role_id


# Internal helpers -----------------------------------------------------------

def _load_cache() -> Dict[str, object]:
    with _lock:
        return _load_cache_locked()


def _load_cache_locked() -> Dict[str, object]:
    global _cache_payload, _cache_mtime
    if not CACHE_PATH.exists():
        refresh_menu_cache()
    current_mtime = CACHE_PATH.stat().st_mtime
    if _cache_payload is None or _cache_mtime != current_mtime:
        with CACHE_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        _hydrate_from_payload(payload)
        _cache_payload = payload
        _cache_mtime = current_mtime
    return _cache_payload or {}


def _hydrate_from_payload(payload: Dict[str, object]) -> None:
    global _menu_index, _role_menu_index
    global _default_role_id, _anonymous_role_id, _admin_role_id
    global _super_admin_role_id, _sys_admin_role_id
    global _super_admin_emails, _sys_admin_emails
    global _cache_payload

    _cache_payload = payload

    roles = payload.get("roles", [])
    menus = payload.get("menu_items", [])
    links = payload.get("menu_in_roles", [])
    overrides = payload.get("overrides", {})

    _menu_index = {
        int(record["id"]): record
        for record in menus  # type: ignore[arg-type]
    }

    _role_menu_index = {}
    for entry in links:  # type: ignore[assignment]
        rid = int(entry["role_id"])
        mid = int(entry["menu_id"])
        _role_menu_index.setdefault(rid, set()).add(mid)

    _default_role_id = None
    _anonymous_role_id = None
    _admin_role_id = None
    _super_admin_role_id = None
    _sys_admin_role_id = None
    for role in roles:  # type: ignore[assignment]
        rid = int(role["id"])
        name = str(role.get("name", "")).lower()
        if name == "user":
            _default_role_id = rid
        elif name == "anonymous":
            _anonymous_role_id = rid
        elif name == "admin":
            _admin_role_id = rid
        elif name == "superadmin":
            _super_admin_role_id = rid
        elif name == "sysadmin":
            _sys_admin_role_id = rid

    _super_admin_emails = set()
    _sys_admin_emails = set()
    if isinstance(overrides, dict):
        for email in overrides.get("super_admin_emails", []):
            if isinstance(email, str) and email.strip():
                _super_admin_emails.add(email.strip().lower())
        for email in overrides.get("sys_admin_emails", []):
            if isinstance(email, str) and email.strip():
                _sys_admin_emails.add(email.strip().lower())


def _include_parent_chain(menu_ids: Set[int]) -> Set[int]:
    expanded = set()

    def _walk(mid: int) -> None:
        if mid in expanded:
            return
        record = _menu_index.get(mid)
        if not record:
            return
        expanded.add(mid)
        parent_id = record.get("parent_id")
        if parent_id:
            _walk(int(parent_id))

    for menu_id in menu_ids:
        _walk(menu_id)
    return expanded
