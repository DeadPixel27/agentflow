import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { StepRun } from "@/lib/api";

interface StepStatusListProps {
  steps: StepRun[];
}

export function StepStatusList({ steps }: StepStatusListProps) {
  return (
    <div className="space-y-2">
      {steps.map((step) => (
        <div
          key={step.step_order}
          className="flex items-center justify-between rounded-lg border px-4 py-3"
        >
          <div>
            <p className="font-medium text-sm">
              Step {step.step_order}: {step.agent_type}
            </p>
            {step.error_message && (
              <p className="text-sm text-destructive mt-1">{step.error_message}</p>
            )}
          </div>
          <Badge variant={step.status === "completed" ? "default" : "destructive"}>
            {step.status}
          </Badge>
        </div>
      ))}
    </div>
  );
}

interface ResultsTableProps {
  rows: Record<string, unknown>[];
}

export function ResultsTable({ rows }: ResultsTableProps) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground">No rows in result.</p>
    );
  }

  const columns = Object.keys(rows[0]).filter((k) => k !== "flags");

  return (
    <div className="rounded-lg border overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col}>{col}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              {columns.map((col) => (
                <TableCell key={col} className="max-w-xs truncate">
                  {formatCell(row[col])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
