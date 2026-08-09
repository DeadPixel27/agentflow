"use client";

import { Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, joinWaitlist } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { loadStoredUser } from "@/lib/user-session";
import { cn } from "@/lib/utils";

function PricingCard({
  title,
  price,
  features,
  cta,
  highlight,
}: {
  title: string;
  price: string;
  features: string[];
  cta: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-6 space-y-5 flex flex-col",
        highlight
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border bg-card",
      )}
    >
      <div>
        <h3 className="font-serif text-lg font-semibold">{title}</h3>
        <p className="text-2xl font-bold mt-1">{price}</p>
      </div>
      <ul className="space-y-2 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      {cta}
    </div>
  );
}

export default function PricingPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [joined, setJoined] = useState(false);

  const stored = loadStoredUser();

  async function handleJoinWaitlist(e: React.FormEvent) {
    e.preventDefault();
    const waitlistEmail = email.trim() || stored?.email || "";
    if (!waitlistEmail) {
      toastError("Email is required.");
      return;
    }

    setLoading(true);
    try {
      const result = await joinWaitlist(
        waitlistEmail,
        name.trim() || stored?.name || "",
        "pricing_page",
      );
      setJoined(true);
      toastSuccess(result.message);
    } catch (err) {
      toastError(
        err instanceof ApiError ? err.message : "Failed to join waitlist.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="v2-page">
      <PageHeader
        title="Pricing"
        description="Extract data from any document with AI"
      />
      <main className="flex-1 overflow-y-auto px-4 py-8">
        <div className="mx-auto max-w-[800px] space-y-10">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PricingCard
              title="Free"
              price="$0"
              features={[
                "50 pages/month",
                "All templates (invoice, receipt, contract, etc.)",
                "Chat refinement",
                "CSV & JSON export",
                "Email delivery",
                "Google Sheets push",
              ]}
              cta={
                <Link href="/">
                  <Button variant="outline" className="w-full">
                    Start extracting
                  </Button>
                </Link>
              }
            />

            <PricingCard
              title="Pro"
              price="Coming soon"
              highlight
              features={[
                "Unlimited pages",
                "Priority extraction (faster models)",
                "Custom templates",
                "API access",
                "Webhook integrations",
                "Priority support",
              ]}
              cta={
                joined ? (
                  <div className="flex items-center justify-center gap-2 py-2 text-sm text-primary font-medium">
                    <Check className="h-4 w-4" />
                    You&apos;re on the list!
                  </div>
                ) : (
                  <form onSubmit={handleJoinWaitlist} className="space-y-3">
                    {!stored?.email && (
                      <>
                        <div className="space-y-1">
                          <Label htmlFor="waitlist-email" className="text-xs">
                            Email
                          </Label>
                          <Input
                            id="waitlist-email"
                            type="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            disabled={loading}
                            required
                          />
                        </div>
                        <div className="space-y-1">
                          <Label htmlFor="waitlist-name" className="text-xs">
                            Name (optional)
                          </Label>
                          <Input
                            id="waitlist-name"
                            placeholder="Your name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={loading}
                          />
                        </div>
                      </>
                    )}
                    <Button type="submit" className="w-full" disabled={loading}>
                      {loading && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      {stored?.email ? "Join waitlist" : "Join Pro waitlist"}
                    </Button>
                  </form>
                )
              }
            />
          </div>

          <div className="text-center text-sm text-muted-foreground space-y-1">
            <p>
              Questions?{" "}
              <a
                href="mailto:kabir@agentflow.app"
                className="text-primary underline"
              >
                kabir@agentflow.app
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
