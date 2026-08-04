import { createUser } from "@/lib/api";

const USER_ID_KEY = "agentflow_user_id";
const USER_NAME_KEY = "agentflow_user_name";

export function getStoredUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(USER_ID_KEY);
}

export async function ensureUser(): Promise<string> {
  const existing = getStoredUserId();
  if (existing) return existing;

  const name =
    localStorage.getItem(USER_NAME_KEY) ??
    `User ${Math.random().toString(36).slice(2, 7)}`;
  const user = await createUser(name);
  localStorage.setItem(USER_ID_KEY, user.user_id);
  localStorage.setItem(USER_NAME_KEY, user.name);
  return user.user_id;
}
