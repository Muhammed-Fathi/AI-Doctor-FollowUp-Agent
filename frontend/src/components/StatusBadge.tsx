import { DEPENDENCY_LABELS, type DependencyState } from "../app/constants";

interface StatusBadgeProps {
  readonly state: DependencyState | "degraded";
  readonly label?: string;
}

const STATE_CLASS: Record<StatusBadgeProps["state"], string> = {
  ok: "badge badge--ok",
  degraded: "badge badge--warn",
  unavailable: "badge badge--warn",
  not_configured: "badge badge--neutral",
};

/** Small, accessible state pill used by the health table and the header. */
export function StatusBadge({ state, label }: StatusBadgeProps) {
  const text =
    label ?? (state === "degraded" ? "Degraded" : DEPENDENCY_LABELS[state]);

  return (
    <span className={STATE_CLASS[state]} data-testid={`badge-${state}`}>
      {text}
    </span>
  );
}
