export const ROLE_ORDER = [
  "general_user",
  "support_user",
  "senior_support_user",
  "administration_user",
  "system_manager",
];

export const ROLE_LABELS = {
  general_user: "General User",
  support_user: "Support User",
  senior_support_user: "Senior Support User",
  administration_user: "Administration User",
  system_manager: "System Manager",
};

export function normalizeRole(role) {
  return ROLE_ORDER.includes(role) ? role : "general_user";
}

export function hasRole(role, minimumRole) {
  return ROLE_ORDER.indexOf(normalizeRole(role)) >= ROLE_ORDER.indexOf(normalizeRole(minimumRole));
}

export function roleLabel(role) {
  return ROLE_LABELS[normalizeRole(role)];
}
