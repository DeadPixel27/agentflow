import { createUser, getUser, type User } from "@/lib/api";

const USER_ID_KEY = "agentflow_user_id";
const USER_NAME_KEY = "agentflow_user_name";
const USER_EMAIL_KEY = "agentflow_user_email";

export interface StoredUser {
  user_id: string;
  name: string;
  email: string;
}

export function loadStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  const user_id = localStorage.getItem(USER_ID_KEY);
  const name = localStorage.getItem(USER_NAME_KEY);
  if (!user_id || !name) return null;
  return {
    user_id,
    name,
    email: localStorage.getItem(USER_EMAIL_KEY) ?? "",
  };
}

export function saveStoredUser(user: StoredUser): void {
  localStorage.setItem(USER_ID_KEY, user.user_id);
  localStorage.setItem(USER_NAME_KEY, user.name);
  localStorage.setItem(USER_EMAIL_KEY, user.email);
}

export function clearStoredUser(): void {
  localStorage.removeItem(USER_ID_KEY);
  localStorage.removeItem(USER_NAME_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
}

export function getStoredUserId(): string | null {
  return loadStoredUser()?.user_id ?? null;
}

export async function registerUser(name: string, email = ""): Promise<StoredUser> {
  const user = await createUser(name.trim(), email.trim());
  const stored: StoredUser = {
    user_id: user.user_id,
    name: user.name,
    email: user.email,
  };
  saveStoredUser(stored);
  return stored;
}

export async function ensureUser(): Promise<string> {
  const existing = loadStoredUser();
  if (existing) return existing.user_id;

  const user = await registerUser(
    `User ${Math.random().toString(36).slice(2, 7)}`,
  );
  return user.user_id;
}

export async function refreshStoredUser(): Promise<StoredUser | null> {
  const stored = loadStoredUser();
  if (!stored) return null;
  try {
    const user = await getUser(stored.user_id);
    const updated: StoredUser = {
      user_id: user.user_id,
      name: user.name,
      email: user.email,
    };
    saveStoredUser(updated);
    return updated;
  } catch {
    return stored;
  }
}

export function toStoredUser(user: User): StoredUser {
  return {
    user_id: user.user_id,
    name: user.name,
    email: user.email,
  };
}
