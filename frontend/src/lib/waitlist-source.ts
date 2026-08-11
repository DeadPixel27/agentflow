/** Waitlist attribution sources — stored on waitlist.source */
export const WAITLIST_SOURCES = {
  normal: "normal",
  pagesExhausted: "pages_exhausted",
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
