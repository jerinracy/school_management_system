import * as PopoverPrimitive from "@radix-ui/react-popover";
import { Check, ChevronsUpDown } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Input } from "./input";

export interface ComboboxOption {
  value: string;
  label: string;
}

interface ComboboxProps {
  options: ComboboxOption[];
  value?: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  className?: string;
  "aria-label"?: string;
}

export function Combobox({
  options,
  value,
  onValueChange,
  placeholder,
  searchPlaceholder,
  emptyLabel,
  className,
  "aria-label": ariaLabel,
}: ComboboxProps) {
  const { t } = useTranslation();
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const selected = options.find((opt) => opt.value === value);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((opt) => opt.label.toLowerCase().includes(q));
  }, [options, query]);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-label={ariaLabel}
          className={cn(
            "flex h-8 w-full items-center justify-between gap-2 rounded-md border border-border bg-surface px-2.5 text-xs text-ink shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
            className,
          )}
        >
          <span className={cn("truncate", !selected && "text-ink-subtle")}>
            {selected ? selected.label : (placeholder ?? t("ui.combobox.placeholder"))}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-ink-subtle" />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          sideOffset={4}
          className="z-50 w-[var(--radix-popover-trigger-width)] min-w-[12rem] rounded-md border border-border bg-surface p-1.5 shadow-lg"
        >
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder ?? t("ui.combobox.search")}
            className="mb-1.5 h-7"
          />
          <div id={listId} role="listbox" className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-2 py-3 text-center text-[11px] text-ink-subtle">
                {emptyLabel ?? t("ui.combobox.empty")}
              </p>
            ) : (
              filtered.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onValueChange(opt.value);
                    setOpen(false);
                    setQuery("");
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors hover:bg-canvas",
                    opt.value === value && "bg-primary-soft text-primary font-medium",
                  )}
                >
                  <Check
                    className={cn("h-3.5 w-3.5 shrink-0", opt.value === value ? "opacity-100" : "opacity-0")}
                  />
                  <span className="truncate">{opt.label}</span>
                </button>
              ))
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
