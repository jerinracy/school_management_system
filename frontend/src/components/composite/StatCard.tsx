import { KpiCard, type KpiTone } from "@/components/ui/KpiCard";
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  meta?: string;
  icon: ReactNode;
  tone?: KpiTone;
  loading?: boolean;
}

export function StatCard(props: StatCardProps) {
  return <KpiCard {...props} />;
}
