import { useCountUp } from "../../lib/useCountUp";

export function StatCounter({
  value,
  decimals = 0,
  suffix = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
}) {
  const animated = useCountUp(value);
  return (
    <span>
      {animated.toFixed(decimals)}
      {suffix}
    </span>
  );
}
