"use client";

import { Loader2, MessageSquare, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, refineRun } from "@/lib/api";
import { toastError } from "@/lib/toast";
import { cn } from "@/lib/utils";

interface RefineMessage {
  role: "user" | "assistant";
  text: string;
}

interface RefineChatPanelProps {
  runId: string;
  disabled?: boolean;
  documentCount?: number;
  versionLabel?: string;
  variant?: "card" | "panel";
  onRefined: (newRunId: string, summary: string) => void;
}

export function RefineChatPanel({
  runId,
  disabled,
  documentCount = 1,
  versionLabel,
  variant = "card",
  onRefined,
}: RefineChatPanelProps) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<RefineMessage[]>([]);

  async function handleSend() {
    const text = message.trim();
    if (!text || loading) return;

    setLoading(true);
    setHistory((prev) => [...prev, { role: "user", text }]);
    setMessage("");

    try {
      const result = await refineRun(runId, text);
      setHistory((prev) => [
        ...prev,
        { role: "assistant", text: result.refine_summary },
      ]);
      onRefined(result.run.run_id, result.refine_summary);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Refine failed.");
      setHistory((prev) => prev.slice(0, -1));
      setMessage(text);
    } finally {
      setLoading(false);
    }
  }

  const badgeText = versionLabel
    ? `Refining all ${documentCount} docs · ${versionLabel}`
    : `Refining all ${documentCount} docs`;

  const chatBody = (
    <>
      <div className="flex-1 overflow-y-auto space-y-2 p-4 min-h-0">
        {history.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Describe what to change — the pipeline will update and re-run.
          </p>
        )}
        {history.map((item, index) => (
          <div
            key={index}
            className={cn(
              "rounded-lg px-3 py-2 text-sm max-w-[90%]",
              item.role === "user"
                ? "ml-auto bg-foreground text-background"
                : "bg-surface-2 text-foreground",
            )}
          >
            {item.role === "assistant" && item.text.startsWith("✓") ? (
              <span className="text-green-600">{item.text}</span>
            ) : (
              item.text
            )}
          </div>
        ))}
      </div>
      <div className="shrink-0 border-t border-border p-3 space-y-2">
        <Textarea
          placeholder='e.g. "also extract payment_status"'
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={disabled || loading}
          className="rounded-[7px] resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <Button
          type="button"
          className="w-full"
          onClick={() => void handleSend()}
          disabled={disabled || loading || !message.trim()}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Re-running…
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send
            </>
          )}
        </Button>
      </div>
    </>
  );

  if (variant === "panel") {
    return (
      <aside className="w-[340px] shrink-0 flex flex-col border-l border-border bg-card min-h-0">
        <div className="shrink-0 p-4 border-b border-border space-y-2">
          <h2 className="font-serif text-base font-semibold">Refine</h2>
          <p className="text-xs text-muted-foreground">
            Tell the agent what to change in the extraction.
          </p>
          <span className="v2-badge-success">{badgeText}</span>
        </div>
        {chatBody}
      </aside>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Refine results
        </CardTitle>
        <CardDescription>
          Not quite right? Tell me what to change — I&apos;ll update the pipeline
          and re-run.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {history.length > 0 && (
          <div className="space-y-2 rounded-md border bg-muted/30 p-3 text-sm max-h-48 overflow-y-auto">
            {history.map((item, index) => (
              <p key={index}>
                <span className="font-medium">
                  {item.role === "user" ? "You" : "Agent"}:
                </span>{" "}
                {item.text}
              </p>
            ))}
          </div>
        )}
        <Textarea
          placeholder='e.g. "also extract payment_status and flag unpaid ones"'
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={disabled || loading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <Button
          type="button"
          onClick={() => void handleSend()}
          disabled={disabled || loading || !message.trim()}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Re-running pipeline…
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
