"use client";

import { type ReactNode } from "react";

interface DetailLayoutProps {
  header: ReactNode;
  main: ReactNode;
  sidebar: ReactNode;
}

export function DetailLayout({ header, main, sidebar }: DetailLayoutProps) {
  return (
    <div className="v2-page">
      {header}
      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-[1fr_300px] min-h-0">
        <div className="overflow-y-auto px-4 sm:px-6 py-6 space-y-6 min-h-0">
          {main}
        </div>
        <div className="border-t lg:border-t-0 lg:border-l border-border overflow-y-auto px-4 py-6 bg-surface-2/30 min-h-0">
          {sidebar}
        </div>
      </div>
    </div>
  );
}
