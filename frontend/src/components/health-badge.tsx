import { useQuery } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, Loader2 } from "lucide-react";

import { fetchHealth } from "@/api/client";
import { Badge } from "@/components/ui/badge";

/**
 * Live backend connectivity indicator. Shows explicit loading, online, and
 * error states — bound to the real /health endpoint, never a placeholder.
 */
export function HealthBadge() {
  const { isPending, isError, data } = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
    retry: 1,
  });

  if (isPending) {
    return (
      <Badge variant="secondary" aria-live="polite">
        <Loader2 className="size-3 animate-spin" aria-hidden="true" />
        Connecting…
      </Badge>
    );
  }

  if (isError) {
    return (
      <Badge variant="destructive" aria-live="polite">
        <CircleAlert className="size-3" aria-hidden="true" />
        Backend offline
      </Badge>
    );
  }

  return (
    <Badge variant="success" aria-live="polite">
      <CircleCheck className="size-3" aria-hidden="true" />
      Backend {data.status}
    </Badge>
  );
}
