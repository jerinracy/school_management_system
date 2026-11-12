import type { LabelHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function FormField({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("space-y-1", className)}>{children}</div>;
}

export function FormLabel({
  className,
  required,
  children,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement> & { required?: boolean }) {
  return (
    <label className={cn("block text-xs font-medium text-ink", className)} {...props}>
      {children}
      {required ? <span className="ml-0.5 text-rose-600">*</span> : null}
    </label>
  );
}

export function FormDescription({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-[11px] text-ink-subtle", className)}>{children}</p>;
}

export function FormMessage({ children, className }: { children?: ReactNode; className?: string }) {
  if (!children) return null;
  return (
    <p role="alert" className={cn("text-[11px] font-medium text-rose-600", className)}>
      {children}
    </p>
  );
}
