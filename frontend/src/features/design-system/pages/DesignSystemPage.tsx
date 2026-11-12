import { useState } from "react";
import { useTranslation } from "react-i18next";
import { GraduationCap } from "lucide-react";
import { ConfirmDialog } from "@/components/composite/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/composite/DataTable";
import { EmptyState } from "@/components/composite/EmptyState";
import { FileUpload } from "@/components/composite/FileUpload";
import { FilterBar } from "@/components/composite/FilterBar";
import { PageHeader } from "@/components/composite/PageHeader";
import { StatCard } from "@/components/composite/StatCard";
import { StatusChip } from "@/components/composite/StatusChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Combobox } from "@/components/ui/combobox";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";

interface SampleRow {
  id: string;
  name: string;
  roll: string;
  status: "present" | "late";
}

const SAMPLE_ROWS: SampleRow[] = [
  { id: "1", name: "Tanvir Ahmed", roll: "101", status: "present" },
  { id: "2", name: "Nusrat Jahan", roll: "102", status: "late" },
];

export function DesignSystemPage() {
  const { t } = useTranslation();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [comboValue, setComboValue] = useState("class-6");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [page, setPage] = useState(1);

  const columns: DataTableColumn<SampleRow>[] = [
    { id: "roll", header: "Roll", sortable: true, cell: (row) => row.roll },
    { id: "name", header: "Student", sortable: true, cell: (row) => row.name },
    {
      id: "status",
      header: "Status",
      cell: (row) => (
        <StatusChip
          label={row.status === "present" ? "Present" : "Late"}
          tone={row.status === "present" ? "success" : "warning"}
        />
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("designSystem.title")}
        subtitle={t("designSystem.subtitle")}
        breadcrumbs={[{ label: t("nav.overview"), to: "/" }, { label: t("designSystem.title") }]}
        actions={
          <Button onClick={() => toast.success("Design token toast triggered")}>
            {t("designSystem.triggerToast")}
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard
          label="Total Students"
          value="1,240"
          meta="Main Campus"
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          tone="success"
        />
        <StatCard
          label="Late Arrivals"
          value="18"
          meta="Today"
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          tone="warning"
        />
        <StatCard
          label="Loading State"
          value="..."
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          loading
        />
      </div>

      <Tabs defaultValue="primitives">
        <TabsList>
          <TabsTrigger value="primitives">Primitives</TabsTrigger>
          <TabsTrigger value="table">DataTable</TabsTrigger>
          <TabsTrigger value="upload">Upload & Empty</TabsTrigger>
        </TabsList>

        <TabsContent value="primitives">
          <Card>
            <CardHeader>
              <CardTitle>Buttons, Badges, Inputs & Pickers</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Button>Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
                  Open Confirm
                </Button>
                <Badge variant="primary">Active</Badge>
                <Badge variant="amber">Pending</Badge>
                <Badge variant="danger">Overdue</Badge>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Input placeholder="Student name or roll..." />
                <Combobox
                  value={comboValue}
                  onValueChange={setComboValue}
                  options={[
                    { value: "class-6", label: "Class 6 — Section A" },
                    { value: "class-7", label: "Class 7 — Section B" },
                  ]}
                />
                <DatePicker value={selectedDate} onChange={setSelectedDate} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="table">
          <FilterBar />
          <DataTable
            rows={SAMPLE_ROWS}
            columns={columns}
            getRowId={(r) => r.id}
            page={page}
            pageSize={10}
            totalCount={2}
            onPageChange={setPage}
            selectable
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
          />
        </TabsContent>

        <TabsContent value="upload" className="space-y-3">
          <FileUpload onFileSelect={() => toast.info("File selected")} progress={65} />
          <EmptyState title="No records found" description="Adjust filters or add a new entry." />
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Confirm Action"
        description="Are you sure you want to proceed with this action?"
        impactSummary="This will update 32 student records in Class 6-A."
        destructive
        onConfirm={() => {
          setConfirmOpen(false);
          toast.success("Confirmed");
        }}
      />
    </div>
  );
}
