// The API speaks integer paise/kg/meters. Only display code converts —
// keep raw integers everywhere else to avoid rounding drift.

export function paiseToRupees(paise: number): string {
  return (paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function paisePerTonneToRupees(paisePerTonne: number): string {
  return paiseToRupees(paisePerTonne);
}

export function kgToTonnes(kg: number): string {
  return (kg / 1000).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

export function metersToKm(m: number | null): string {
  if (m === null) return "unknown";
  return (m / 1000).toLocaleString("en-IN", { maximumFractionDigits: 1 }) + " km";
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatWindow(start: string, end: string): string {
  return `${formatDateTime(start)} – ${formatDateTime(end)}`;
}
