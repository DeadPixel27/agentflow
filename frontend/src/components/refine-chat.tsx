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

interface RefineMessage {
  role: "user" | "assistant";
  text: string;
}

interface RefineChatPanelProps {
  runId: string;
  disabled?: boolean;
  onRefined: (newRunId: string, summary: string) => void;
}

export function RefineChatPanel({
  runId,
  disabled,
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
