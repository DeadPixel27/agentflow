export type ResultsLayout = "horizontal" | "vertical";

const STORAGE_KEY = "nexora:results-layout";

export function loadResultsLayout(): ResultsLayout {
  if (typeof window === "undefined") return "vertical";
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "horizontal" || value === "vertical") return value;
  } catch {
    /* ignore */
  }
  return "vertical";
}

export function saveResultsLayout(layout: ResultsLayout): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, layout);
  } catch {
    /* ignore */
  }
}
