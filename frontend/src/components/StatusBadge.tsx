type Tone = "neutral" | "positive" | "warning" | "negative";

const TONE_BY_STATUS: Record<string, Tone> = {
  open: "positive",
  closed: "neutral",
  fulfilled: "neutral",
  queued: "warning",
  running: "warning",
  agreed: "positive",
  no_deal: "negative",
  failed: "negative",
  pickup_scheduled: "warning",
  collected: "warning",
  delivered: "positive",
  cancelled: "negative",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = TONE_BY_STATUS[status] ?? "neutral";
  return <span className={`badge badge--${tone}`}>{status.replace(/_/g, " ")}</span>;
}
