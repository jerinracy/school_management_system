import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { DataTable, type DataTableColumn } from "@/components/composite/DataTable";
import i18n from "@/i18n";

interface Row {
  id: string;
  name: string;
}

const COLUMNS: DataTableColumn<Row>[] = [
  { id: "id", header: "ID", sortable: true, cell: (r) => r.id },
  { id: "name", header: "Name", sortable: true, cell: (r) => r.name },
];

describe("DataTable", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders rows, supports sorting and bulk selection", async () => {
    const user = userEvent.setup();
    const onSort = vi.fn();
    const onSelectionChange = vi.fn();

    render(
      <DataTable
        rows={[{ id: "1", name: "Ayesha" }]}
        columns={COLUMNS}
        getRowId={(r) => r.id}
        page={1}
        pageSize={10}
        totalCount={1}
        onPageChange={vi.fn()}
        onSortChange={onSort}
        selectable
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
      />,
    );

    expect(screen.getByText("Ayesha")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Name/i }));
    expect(onSort).toHaveBeenCalledWith("name");

    await user.click(screen.getByRole("checkbox", { name: "Select row" }));
    expect(onSelectionChange).toHaveBeenCalledWith(["1"]);
  });

  it("renders empty and error states", () => {
    const { rerender } = render(
      <DataTable
        rows={[]}
        columns={COLUMNS}
        getRowId={(r) => r.id}
        page={1}
        pageSize={10}
        totalCount={0}
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByText("No records found")).toBeInTheDocument();

    rerender(
      <DataTable
        rows={[]}
        columns={COLUMNS}
        getRowId={(r) => r.id}
        page={1}
        pageSize={10}
        totalCount={0}
        onPageChange={vi.fn()}
        error
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(
      <DataTable
        rows={[{ id: "1", name: "Ayesha" }]}
        columns={COLUMNS}
        getRowId={(r) => r.id}
        page={1}
        pageSize={10}
        totalCount={1}
        onPageChange={vi.fn()}
        selectable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
      />,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
