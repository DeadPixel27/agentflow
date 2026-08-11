import { type ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="shrink-0 border-b border-border px-4 sm:px-6 py-5 flex items-start justify-between gap-4">
      <div>
        <h1 className="font-serif text-lg font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
