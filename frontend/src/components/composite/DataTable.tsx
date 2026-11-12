import { ArrowUpDown, Columns3 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "./EmptyState";
import { ErrorPage } from "./ErrorPage";

export interface DataTableColumn<T> {
  id: string;
  header: string;
  sortable?: boolean;
  hideable?: boolean;
  cell: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: DataTableColumn<T>[];
  getRowId: (row: T) => string;
  page: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (nextPage: number) => void;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  onSortChange?: (columnId: string) => void;
  selectable?: boolean;
  selectedIds?: string[];
  onSelectionChange?: (ids: string[]) => void;
  renderRowActions?: (row: T) => ReactNode;
  loading?: boolean;
  error?: boolean;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function DataTable<T>({
  rows,
  columns,
  getRowId,
  page,
  pageSize,
  totalCount,
  onPageChange,
  sortBy,
  sortDir,
  onSortChange,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
  renderRowActions,
  loading = false,
  error = false,
  onRetry,
  emptyTitle,
  emptyDescription,
}: DataTableProps<T>) {
  const { t } = useTranslation();
  const [hiddenCols, setHiddenCols] = useState<Record<string, boolean>>({});

  const visibleColumns = columns.filter((col) => !hiddenCols[col.id]);
  const allSelected = rows.length > 0 && rows.every((row) => selectedIds.includes(getRowId(row)));

  const toggleAll = () => {
    if (!onSelectionChange) return;
    if (allSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(rows.map(getRowId));
    }
  };

  const toggleOne = (id: string) => {
    if (!onSelectionChange) return;
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((item) => item !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  if (error) {
    return <ErrorPage onRetry={onRetry} />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-[0_1px_2px_rgba(17,24,39,0.03)]">
      <div className="flex items-center justify-end border-b border-border px-3 py-1.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <Columns3 className="h-3.5 w-3.5" />
              <span>{t("ui.table.columns")}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {columns
              .filter((c) => c.hideable !== false)
              .map((col) => {
                const isVisible = !hiddenCols[col.id];
                return (
                  <DropdownMenuItem
                    key={col.id}
                    onSelect={(e) => {
                      e.preventDefault();
                      setHiddenCols((prev) => ({ ...prev, [col.id]: isVisible }));
                    }}
                  >
                    <Checkbox checked={isVisible} aria-hidden="true" />
                    <span>{col.header}</span>
                  </DropdownMenuItem>
                );
              })}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {loading ? (
        <div className="space-y-2 p-4" aria-busy="true">
          {Array.from({ length: 4 }).map((_, idx) => (
            <Skeleton key={idx} className="h-8 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="p-4">
          <EmptyState
            title={emptyTitle ?? t("ui.table.emptyTitle")}
            description={emptyDescription ?? t("ui.table.emptyDescription")}
          />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {selectable ? (
                <TableHead className="w-10">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={toggleAll}
                    aria-label={t("ui.table.selectAll")}
                  />
                </TableHead>
              ) : null}
              {visibleColumns.map((col) => (
                <TableHead key={col.id}>
                  {col.sortable && onSortChange ? (
                    <button
                      type="button"
                      onClick={() => onSortChange(col.id)}
                      className="inline-flex items-center gap-1 font-semibold uppercase tracking-wider hover:text-ink"
                    >
                      <span>{col.header}</span>
                      <ArrowUpDown
                        className="h-3 w-3"
                        aria-label={
                          sortBy === col.id ? `${col.header} (${sortDir ?? "asc"})` : col.header
                        }
                      />
                    </button>
                  ) : (
                    col.header
                  )}
                </TableHead>
              ))}
              {renderRowActions ? (
                <TableHead className="text-right">{t("ui.table.actions")}</TableHead>
              ) : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const id = getRowId(row);
              const isSelected = selectedIds.includes(id);
              return (
                <TableRow key={id} data-state={isSelected ? "selected" : undefined}>
                  {selectable ? (
                    <TableCell>
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleOne(id)}
                        aria-label={t("ui.table.selectRow")}
                      />
                    </TableCell>
                  ) : null}
                  {visibleColumns.map((col) => (
                    <TableCell key={col.id}>{col.cell(row)}</TableCell>
                  ))}
                  {renderRowActions ? (
                    <TableCell className="text-right">{renderRowActions(row)}</TableCell>
                  ) : null}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      <Pagination
        page={page}
        pageSize={pageSize}
        totalCount={totalCount}
        onPageChange={onPageChange}
      />
    </div>
  );
}
