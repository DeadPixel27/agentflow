"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useSignIn } from "@/hooks/use-sign-in";
import { useUser } from "@/hooks/use-user";
import { toastSuccess } from "@/lib/toast";
import { clearStoredUser } from "@/lib/user-session";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/workflows", label: "Workflows" },
  { href: "/pricing", label: "Pricing" },
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return (parts[0]?.[0] ?? "A").toUpperCase();
}

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, setUser } = useUser();
  const { openSignIn } = useSignIn();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function handleSignOut() {
    clearStoredUser();
    setUser(null);
    setOpen(false);
    toastSuccess("Signed out.");
    router.push("/");
  }

  return (
    <header className="shrink-0 border-b border-border bg-card/90 backdrop-blur-sm z-50">
      <div className="flex h-14 items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 shrink-0">
            <span className="flex h-[26px] w-[26px] items-center justify-center rounded-md bg-foreground text-[11px] font-bold text-background">
              A
            </span>
            <span className="text-sm font-semibold tracking-tight">AgentFlow</span>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {NAV_LINKS.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-[13px] transition-colors",
                    active
                      ? "bg-surface-hover font-semibold text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-surface-hover/60",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="relative" ref={menuRef}>
          {user ? (
            <>
              <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground"
                aria-label="Account menu"
              >
                {initials(user.name)}
              </button>
              {open && (
                <div className="absolute right-0 top-full mt-2 w-52 rounded-lg border border-border bg-card py-1 shadow-lg z-50">
                  <div className="px-3 py-2 border-b border-border">
                    <p className="text-[13px] font-semibold truncate">{user.name}</p>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {user.email}
                    </p>
                  </div>
                  <Link
                    href="/account"
                    className="block w-full px-3 py-2 text-left text-[13px] hover:bg-muted"
                    onClick={() => setOpen(false)}
                  >
                    Account Settings
                  </Link>
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left text-[13px] hover:bg-muted"
                    onClick={() => {
                      setOpen(false);
                      router.push("/account");
                    }}
                  >
                    Integrations
                  </button>
                  <div className="my-1 border-t border-border" />
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left text-[13px] text-destructive hover:bg-muted"
                    onClick={handleSignOut}
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={openSignIn}
              className="text-[13px] font-medium text-primary hover:underline"
            >
              Sign in
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
