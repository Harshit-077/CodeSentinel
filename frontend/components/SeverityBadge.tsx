import { clsx } from "clsx";

type Severity = "critical" | "high" | "medium" | "low" | "info";

const styles: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-400 border border-red-500/30",
  high:     "bg-orange-500/20 text-orange-400 border border-orange-500/30",
  medium:   "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  low:      "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  info:     "bg-gray-500/20 text-gray-400 border border-gray-500/30",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const s = (severity?.toLowerCase() as Severity) ?? "info";
  return (
    <span className={clsx("badge", styles[s] ?? styles.info)}>
      {s}
    </span>
  );
}