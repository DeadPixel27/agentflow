/** Waitlist attribution sources — stored on waitlist.source */
export const WAITLIST_SOURCES = {
  normal: "normal",
  pagesExhausted: "pages_exhausted",
  emailsExhausted: "emails_exhausted",
  sheetsExhausted: "sheets_exhausted",
  refinesExhausted: "refines_exhausted",
  inboundEmail: "inbound_email",
} as const;

export type WaitlistSource =
  (typeof WAITLIST_SOURCES)[keyof typeof WAITLIST_SOURCES];

const ALLOWED = new Set<string>(Object.values(WAITLIST_SOURCES));

/** Map legacy / unknown query values to a known source. */
export function normalizeWaitlistSource(
  raw: string | null | undefined,
): WaitlistSource {
  if (!raw) return WAITLIST_SOURCES.normal;
  if (raw === "pricing_page") return WAITLIST_SOURCES.normal;
  if (ALLOWED.has(raw)) return raw as WaitlistSource;
  return WAITLIST_SOURCES.normal;
}

export function pricingHref(source: WaitlistSource = WAITLIST_SOURCES.normal): string {
  if (source === WAITLIST_SOURCES.normal) return "/pricing";
  return `/pricing?source=${encodeURIComponent(source)}`;
}

/** Pick waitlist attribution from a backend 429 detail message. */
export function waitlistSourceFromLimitMessage(
  message: string | undefined,
): WaitlistSource {
  const text = (message || "").toLowerCase();
  if (text.includes("email")) return WAITLIST_SOURCES.emailsExhausted;
  if (text.includes("sheets")) return WAITLIST_SOURCES.sheetsExhausted;
  if (text.includes("refinement") || text.includes("refine")) {
    return WAITLIST_SOURCES.refinesExhausted;
  }
  return WAITLIST_SOURCES.pagesExhausted;
}
