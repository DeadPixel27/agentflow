"use client";

import { useCallback, useEffect, useState } from "react";

import {
  loadStoredUser,
  refreshStoredUser,
  type StoredUser,
} from "@/lib/user-session";

export function useUser() {
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

  return { user, ready, reload, setUser };
}
