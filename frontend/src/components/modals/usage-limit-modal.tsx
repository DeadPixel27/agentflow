"use client";

import { AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import { ModalShell } from "@/components/modals/modal-shell";
import { Button } from "@/components/ui/button";
import { pricingHref, WAITLIST_SOURCES } from "@/lib/waitlist-source";

interface UsageLimitModalProps {
  open: boolean;
  onClose: () => void;
  message?: string;
}

export function UsageLimitModal({
  open,
  onClose,
  message,
}: UsageLimitModalProps) {
  const router = useRouter();

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Free limit reached"
      description={
        message ||
        "You've used all 50 free pages this month. Join the Pro waitlist for unlimited access."
      }
      className="sm:max-w-[420px]"
      footer={
        <>
          <Button
            variant="outline"
            onClick={onClose}
          >
            Maybe later
          </Button>
          <Button
            onClick={() => {
              onClose();
              router.push(pricingHref(WAITLIST_SOURCES.pagesExhausted));
            }}
          >
            Join Pro Waitlist
          </Button>
        </>
      }
    >
      <div className="flex items-center gap-2 text-amber-600">
        <AlertTriangle className="h-5 w-5 shrink-0" />
        <p className="text-sm">
          Upgrade interest helps us prioritize Pro features for power users.
        </p>
      </div>
    </ModalShell>
  );
}
