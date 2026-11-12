import { Toaster as SonnerToaster, toast } from "sonner";
import { useTheme } from "@/lib/theme";

export function Toaster() {
  const { theme } = useTheme();
  return (
    <SonnerToaster
      theme={theme}
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "border border-border bg-surface text-ink text-xs shadow-md",
          description: "text-ink-muted text-[11px]",
        },
      }}
    />
  );
}

export { toast };
