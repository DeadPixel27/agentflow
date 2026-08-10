"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  loadStoredUser,
  refreshStoredUser,
  type StoredUser,
} from "@/lib/user-session";

interface UserContextValue {
  user: StoredUser | null;
  ready: boolean;
  reload: () => Promise<void>;
  setUser: (user: StoredUser | null) => void;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(null);
  const [ready, setReady] = useState(false);

  const reload = useCallback(async () => {
    const stored = loadStoredUser();
    if (!stored) {
      setUser(null);
      return;
    }
    const refreshed = await refreshStoredUser();
    setUser(refreshed);
  }, []);

  useEffect(() => {
    const stored = loadStoredUser();
    setUser(stored);
    setReady(true);
    if (stored) {
      void refreshStoredUser().then(setUser);
    }
  }, []);

  const value = useMemo(
    () => ({ user, ready, reload, setUser }),
    [user, ready, reload],
  );

  return (
    <UserContext.Provider value={value}>{children}</UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return ctx;
}
