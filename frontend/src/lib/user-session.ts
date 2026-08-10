import {
  clearAccessToken,
  getAccessToken,
  getUser,
  setAccessToken,
  signIn,
  signInWithGoogle as apiSignInWithGoogle,
  type User,
} from "@/lib/api";

const USER_ID_KEY = "agentflow_user_id";
const USER_NAME_KEY = "agentflow_user_name";
const USER_EMAIL_KEY = "agentflow_user_email";

export interface StoredUser {
  user_id: string;
  name: string;
  email: string;
}

export class SignInRequiredError extends Error {
  constructor(message = "Sign in required") {
    super(message);
    this.name = "SignInRequiredError";
  }
}

export function isEmailAuthAllowed(): boolean {
  return process.env.NEXT_PUBLIC_AUTH_ALLOW_EMAIL === "true";
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
  clearAccessToken();
}

export function getStoredUserId(): string | null {
  return loadStoredUser()?.user_id ?? null;
}

function storeSession(result: {
  user: User;
  is_new_user: boolean;
  token: string;
}): { user: StoredUser; isNewUser: boolean } {
  setAccessToken(result.token);
  const stored: StoredUser = {
    user_id: result.user.user_id,
    name: result.user.name,
    email: result.user.email,
  };
  saveStoredUser(stored);
  return { user: stored, isNewUser: result.is_new_user };
}

/** Sign in by email (dev/local when AUTH_ALLOW_EMAIL is enabled). */
export async function signInUser(
  name: string,
  email: string,
): Promise<{ user: StoredUser; isNewUser: boolean }> {
  const result = await signIn(name.trim(), email.trim());
  return storeSession(result);
}

/** Sign in with a Google Identity Services ID token. */
export async function signInWithGoogle(
  idToken: string,
): Promise<{ user: StoredUser; isNewUser: boolean }> {
  const result = await apiSignInWithGoogle(idToken);
  return storeSession(result);
}

/** @deprecated Use signInUser */
export async function registerUser(name: string, email = ""): Promise<StoredUser> {
  const { user } = await signInUser(name, email);
  return user;
}

export async function ensureUser(): Promise<string> {
  const existing = loadStoredUser();
  if (existing?.email && getAccessToken()) {
    return existing.user_id;
  }
  if (isEmailAuthAllowed()) {
    if (existing?.email) {
      const refreshed = await signInUser(existing.name, existing.email);
      return refreshed.user.user_id;
    }
    const user = await signInUser(
      `User ${Math.random().toString(36).slice(2, 7)}`,
      `anon-${Math.random().toString(36).slice(2, 9)}@local.dev`,
    );
    return user.user.user_id;
  }
  throw new SignInRequiredError();
}

export async function refreshStoredUser(): Promise<StoredUser | null> {
  const stored = loadStoredUser();
  if (!stored) return null;
  if (!getAccessToken() && stored.email && isEmailAuthAllowed()) {
    try {
      const refreshed = await signInUser(stored.name, stored.email);
      return refreshed.user;
    } catch {
      return stored;
    }
  }
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
