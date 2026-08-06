"use client";

import {
  Briefcase,
  CreditCard,
  FileText,
  HeartPulse,
  Home,
  Loader2,
  Package,
  Receipt,
  Scale,
  User,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  getTemplate,
  listTemplates,
  type PipelineTemplate,
  type PipelineTemplateSummary,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, typeof FileText> = {
  receipt: Receipt,
  user: User,
  scale: Scale,
  "credit-card": CreditCard,
  package: Package,
  home: Home,
  "heart-pulse": HeartPulse,
  finance: Receipt,
  hr: Briefcase,
  legal: Scale,
  medical: HeartPulse,
  real_estate: Home,
};

interface TemplatePickerProps {
  selectedId: string | null;
  onSelect: (template: PipelineTemplate) => void;
  onClear?: () => void;
  disabled?: boolean;
}

export function TemplatePicker({
  selectedId,
  onSelect,
  disabled,
}: TemplatePickerProps) {
  const [templates, setTemplates] = useState<PipelineTemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listTemplates();
        if (!cancelled) setTemplates(data.templates);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError ? e.message : "Could not load templates.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSelect(summary: PipelineTemplateSummary) {
    try {
      const full = await getTemplate(summary.template_id);
      onSelect({
        ...summary,
        ...full,
        default_task: full.default_task || full.task_description || "",
      });
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Could not load template details.",
      );
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading templates…
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-amber-700 py-2">
        Could not load templates: {error}. Is the backend running on{" "}
        {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}?
      </p>
    );
  }

  if (!templates.length) {
    return (
      <p className="text-sm text-muted-foreground py-2">
        No templates available. Restart the backend to load code-defined templates.
      </p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {templates.map((template) => {
        const Icon = ICON_MAP[template.icon] ?? ICON_MAP[template.category] ?? FileText;
        const isSelected = selectedId === template.template_id;
        return (
          <button
            key={template.template_id}
            type="button"
            disabled={disabled}
            onClick={() => handleSelect(template)}
            className={cn(
              "text-left rounded-lg border p-3 transition-colors hover:bg-muted/50 disabled:opacity-50",
              isSelected && "border-primary bg-primary/5 ring-1 ring-primary",
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{template.name}</span>
                  <Badge variant="outline" className="text-[10px] capitalize">
                    {template.category.replace("_", " ")}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {template.description}
                </p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

export function TemplatePickerSection({
  selectedId,
  onSelect,
  onClear,
  disabled,
}: TemplatePickerProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Start from a template</CardTitle>
        <CardDescription>
          Pick a preset — we&apos;ll run an optimized pipeline with curated fields
          and domain-specific extraction rules.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <TemplatePicker
          selectedId={selectedId}
          onSelect={onSelect}
          disabled={disabled}
        />
        {selectedId && onClear && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="mt-3 px-0 text-muted-foreground"
            disabled={disabled}
            onClick={onClear}
          >
            Or describe your own task
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
