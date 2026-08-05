"use client";

import Link from "next/link";
import { Menu, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useUser } from "@/hooks/use-user";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "New run" },
  { href: "/workflows", label: "Workflows" },
  { href: "/account", label: "Account" },
];

export function AppHeader() {
  const pathname = usePathname();
  const { user } = useUser();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="font-semibold tracking-tight shrink-0">
            AgentFlow
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm transition-colors",
                  pathname === item.href
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {user ? (
            <p className="text-sm text-muted-foreground truncate max-w-[140px] sm:max-w-[180px]">
              {user.name}
            </p>
          ) : (
            <Link
              href="/account"
              className="text-sm text-primary hover:underline shrink-0"
            >
              Sign in
            </Link>
          )}
          <button
            type="button"
            className="sm:hidden inline-flex h-9 w-9 items-center justify-center rounded-md border border-border hover:bg-muted"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? (
              <X className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="sm:hidden border-t px-4 py-2 space-y-1 bg-background">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "block rounded-md px-3 py-2 text-sm transition-colors",
                pathname === item.href
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
