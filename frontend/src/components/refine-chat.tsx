"use client";

import { Check, Loader2, MessageSquare, Play, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  refinePlan,
  refineRun,
  type RefinePlanMessage,
} from "@/lib/api";
import { toastError } from "@/lib/toast";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  planned_changes?: string[];
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
  const [applying, setApplying] = useState(false);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [readyToApply, setReadyToApply] = useState(false);
  const [accumulatedInstruction, setAccumulatedInstruction] = useState("");

  useEffect(() => {
    setHistory([]);
    setMessage("");
    setReadyToApply(false);
    setAccumulatedInstruction("");
  }, [runId]);

  async function handleSend() {
    const text = message.trim();
    if (!text || loading || applying) return;

    const planHistory: RefinePlanMessage[] = [
      ...history.map((item) => ({ role: item.role, content: item.text })),
      { role: "user", content: text },
    ];

    setLoading(true);
    setMessage("");
    setHistory((prev) => [...prev, { role: "user", text }]);

    try {
      const result = await refinePlan(runId, text, planHistory);

      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.message,
          planned_changes: result.planned_changes,
        },
      ]);

      if (result.ready && result.accumulated_instruction) {
        setReadyToApply(true);
        setAccumulatedInstruction(result.accumulated_instruction);
      } else if (result.ready) {
        setReadyToApply(true);
        setAccumulatedInstruction(
          result.accumulated_instruction ||
            `Apply these refinements: ${(result.planned_changes || []).join("; ")}. User request: ${text}`,
        );
      } else {
        setReadyToApply(false);
        setAccumulatedInstruction("");
      }
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Plan mode failed.");
      setHistory((prev) => prev.slice(0, -1));
      setMessage(text);
    } finally {
      setLoading(false);
    }
  }

  async function handleApply() {
    if (!accumulatedInstruction || applying) return;

    setApplying(true);
    setHistory((prev) => [
      ...prev,
      { role: "assistant", text: "⏳ Applying changes and re-running extraction..." },
    ]);

    try {
      const result = await refineRun(runId, accumulatedInstruction);
      setHistory((prev) => {
        // Replace the "applying..." message with the real summary
        const updated = prev.slice(0, -1);
        return [
          ...updated,
          { role: "assistant", text: `✓ ${result.refine_summary}` },
        ];
      });
      setReadyToApply(false);
      setAccumulatedInstruction("");
      onRefined(result.run.run_id, result.refine_summary);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Refine failed.");
      // Remove the "applying..." message
      setHistory((prev) => prev.slice(0, -1));
    } finally {
      setApplying(false);
    }
  }

  const badgeText = versionLabel
    ? `Refining all ${documentCount} docs · ${versionLabel}`
    : `Refining all ${documentCount} docs`;

  const chatMessages = (
    <div className="flex-1 overflow-y-auto space-y-2 p-4 min-h-0">
      {history.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Describe what to change — I&apos;ll clarify and plan before
          re-running.
        </p>
      )}
      {history.map((item, index) => (
        <div key={index}>
          <div
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
          {/* Show planned changes as pills */}
          {item.planned_changes && item.planned_changes.length > 0 && (
            <div className="mt-1.5 space-y-1 ml-1">
              {item.planned_changes.map((change, i) => (
                <div
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-muted-foreground"
                >
                  <Check className="h-3 w-3 mt-0.5 text-primary shrink-0" />
                  <span>{change}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const inputArea = (
    <div className="shrink-0 border-t border-border p-3 space-y-2">
      <Textarea
        placeholder={
          readyToApply
            ? "Looks good? Click Apply — or keep refining..."
            : 'e.g. "also extract payment_status"'
        }
        rows={3}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={disabled || loading || applying}
        className="rounded-[7px] resize-none"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSend();
          }
        }}
      />
      <div className="flex gap-2">
        <Button
          type="button"
          variant={readyToApply ? "outline" : "default"}
          className="flex-1"
          onClick={() => void handleSend()}
          disabled={disabled || loading || applying || !message.trim()}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Thinking...
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send
            </>
          )}
        </Button>
        {readyToApply && (
          <Button
            type="button"
            className="flex-1"
            onClick={() => void handleApply()}
            disabled={applying}
          >
            {applying ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Re-running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Apply
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );

  if (variant === "panel") {
    return (
      <aside className="w-[340px] shrink-0 flex flex-col border-l border-border bg-card min-h-0">
        <div className="shrink-0 p-4 border-b border-border space-y-2">
          <h2 className="font-serif text-base font-semibold">Refine</h2>
          <p className="text-xs text-muted-foreground">
            Tell me what to change — I&apos;ll plan first, then apply.
          </p>
          <span className="v2-badge-success">{badgeText}</span>
        </div>
        {chatMessages}
        {inputArea}
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
          Not quite right? Tell me what to change — I&apos;ll plan the fix
          before re-running.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {history.length > 0 && (
          <div className="space-y-2 rounded-md border bg-muted/30 p-3 text-sm max-h-48 overflow-y-auto">
            {history.map((item, index) => (
              <div key={index}>
                <p>
                  <span className="font-medium">
                    {item.role === "user" ? "You" : "Agent"}:
                  </span>{" "}
                  {item.role === "assistant" && item.text.startsWith("✓") ? (
                    <span className="text-green-600">{item.text}</span>
                  ) : (
                    item.text
                  )}
                </p>
                {item.planned_changes && item.planned_changes.length > 0 && (
                  <div className="ml-4 mt-1 space-y-0.5">
                    {item.planned_changes.map((change, i) => (
                      <p key={i} className="text-xs text-muted-foreground">
                        • {change}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <Textarea
          placeholder={
            readyToApply
              ? "Looks good? Click Apply — or keep refining..."
              : 'e.g. "also extract payment_status and flag unpaid ones"'
          }
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={disabled || loading || applying}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <div className="flex gap-2">
          <Button
            type="button"
            variant={readyToApply ? "outline" : "default"}
            className="flex-1"
            onClick={() => void handleSend()}
            disabled={disabled || loading || applying || !message.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Thinking...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send
              </>
            )}
          </Button>
          {readyToApply && (
            <Button
              type="button"
              className="flex-1"
              onClick={() => void handleApply()}
              disabled={applying}
            >
              {applying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Re-running...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Apply
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
