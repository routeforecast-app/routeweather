from __future__ import annotations


GENERAL_USER = "general_user"
SUPPORT_USER = "support_user"
SENIOR_SUPPORT_USER = "senior_support_user"
ADMINISTRATION_USER = "administration_user"
SYSTEM_MANAGER = "system_manager"

ROLE_ORDER = [
    GENERAL_USER,
    SUPPORT_USER,
    SENIOR_SUPPORT_USER,
    ADMINISTRATION_USER,
    SYSTEM_MANAGER,
]

ROLE_LABELS = {
    GENERAL_USER: "General User",
    SUPPORT_USER: "Support User",
    SENIOR_SUPPORT_USER: "Senior Support User",
    ADMINISTRATION_USER: "Administration User",
    SYSTEM_MANAGER: "System Manager",
}

ROLE_RANKS = {role: index for index, role in enumerate(ROLE_ORDER)}


def normalize_role(role: str | None) -> str:
    if not role:
        return GENERAL_USER
    normalized = role.strip().lower()
    return normalized if normalized in ROLE_RANKS else GENERAL_USER


def has_role(role: str | None, minimum_role: str) -> bool:
    current_role = normalize_role(role)
    required_role = normalize_role(minimum_role)
    return ROLE_RANKS[current_role] >= ROLE_RANKS[required_role]


def highest_role(*roles: str | None) -> str:
    normalized_roles = [normalize_role(role) for role in roles]
    return max(normalized_roles, key=lambda role: ROLE_RANKS[role], default=GENERAL_USER)


def role_label(role: str | None) -> str:
    return ROLE_LABELS[normalize_role(role)]
