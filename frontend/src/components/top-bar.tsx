import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface TopBarProps {
  backHref: string;
  backLabel?: string;
  title: string;
  meta?: string;
  badge?: ReactNode;
  className?: string;
}

export function TopBar({
  backHref,
  backLabel = "Back",
  title,
  meta,
  badge,
  className,
}: TopBarProps) {
  return (
    <div
      className={cn(
        "shrink-0 flex items-center gap-3 border-b border-border px-4 py-3",
        className,
      )}
    >
      <Link
        href={backHref}
        className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        <span className="sr-only sm:not-sr-only">{backLabel}</span>
      </Link>
      <div className="h-5 w-px bg-border" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="font-serif text-base font-semibold">{title}</h1>
          {badge}
        </div>
        {meta && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">{meta}</p>
        )}
      </div>
    </div>
  );
}
