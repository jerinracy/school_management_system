import { FileUp, X } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { toLocaleDigits } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  accept?: string[];
  maxSizeMb?: number;
  progress?: number;
  onFileSelect: (file: File) => void;
  onClear?: () => void;
}

export function FileUpload({
  accept = [".pdf", ".png", ".jpg", ".jpeg", ".csv"],
  maxSizeMb = 5,
  progress,
  onFileSelect,
  onClear,
}: FileUploadProps) {
  const { t, i18n } = useTranslation();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    setError(null);

    const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (accept.length > 0 && !accept.includes(ext)) {
      setError(t("ui.fileUpload.invalidType", { types: accept.join(", ") }));
      return;
    }

    if (file.size > maxSizeMb * 1024 * 1024) {
      setError(
        t("ui.fileUpload.tooLarge", {
          max: toLocaleDigits(maxSizeMb, i18n.language),
        }),
      );
      return;
    }

    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0]);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border-strong bg-canvas/60 px-4 py-5 text-center">
        <FileUp className="h-5 w-5 text-primary" aria-hidden="true" />
        <p className="mt-1.5 text-xs font-medium text-ink">{t("ui.fileUpload.prompt")}</p>
        <p className="mt-0.5 text-[11px] text-ink-subtle">
          {t("ui.fileUpload.hint", {
            types: accept.join(", "),
            max: toLocaleDigits(maxSizeMb, i18n.language),
          })}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={accept.join(",")}
          onChange={handleChange}
          className="sr-only"
          aria-label={t("ui.fileUpload.chooseFile")}
        />
        <Button
          variant="secondary"
          size="sm"
          className="mt-2.5"
          onClick={() => inputRef.current?.click()}
        >
          {t("ui.fileUpload.chooseFile")}
        </Button>
      </div>

      {error ? (
        <p role="alert" className="text-[11px] font-medium text-rose-600">
          {error}
        </p>
      ) : null}

      {selectedFile ? (
        <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-medium text-ink">{selectedFile.name}</span>
            <button
              type="button"
              aria-label={t("ui.fileUpload.remove")}
              onClick={() => {
                setSelectedFile(null);
                if (inputRef.current) inputRef.current.value = "";
                onClear?.();
              }}
              className="rounded p-0.5 text-ink-subtle hover:bg-canvas hover:text-ink"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          {typeof progress === "number" ? (
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-canvas">
              <div
                className={cn("h-full bg-primary transition-all duration-200")}
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
