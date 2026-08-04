import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link href="/" className="font-semibold tracking-tight">
          AgentFlow
        </Link>
        <p className="text-sm text-muted-foreground hidden sm:block">
          Describe your task. Upload documents. AI does the rest.
        </p>
      </div>
    </header>
  );
}
