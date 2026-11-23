import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Users,
  Plus,
  LogOut,
  DoorOpen,
  Compass,
} from "lucide-react";
import {
  operationsApi,
  type GatePassStatus,
} from "../api/operationsApi";
import {
  hostelAllocationSchema,
  type HostelAllocationFormData,
} from "../schemas/operationsSchemas";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const HostelAllocationsPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"allocations" | "gatepasses">("allocations");
  const [isAllocateOpen, setIsAllocateOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch allocations
  const { data: allocationsData, isLoading: isLoadingAllocations } = useQuery({
    queryKey: ["hostel-allocations"],
    queryFn: () => operationsApi.getHostelAllocations(),
  });

  const allocations = allocationsData?.results || [];

  // Fetch gate passes
  const { data: gatePassesData, isLoading: isLoadingGatePasses } = useQuery({
    queryKey: ["hostel-gate-passes"],
    queryFn: () => operationsApi.getGatePasses(),
  });

  const gatePasses = gatePassesData?.results || [];

  // Mutations
  const allocateMutation = useMutation({
    mutationFn: (data: HostelAllocationFormData) =>
      operationsApi.createHostelAllocation({
        ...data,
        is_active: true,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["hostel-allocations"] });
      void queryClient.invalidateQueries({ queryKey: ["hostel-beds"] });
      setIsAllocateOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.bedAllocated", "Bed allocated to student successfully") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const vacateMutation = useMutation({
    mutationFn: (allocationId: string) =>
      operationsApi.vacateHostelAllocation(allocationId, {
        vacated_date: new Date().toISOString().split("T")[0],
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["hostel-allocations"] });
      void queryClient.invalidateQueries({ queryKey: ["hostel-beds"] });
      setFeedback({ type: "success", message: t("operations.bedVacated", "Student marked as vacated and bed freed") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<HostelAllocationFormData>({
    resolver: zodResolver(hostelAllocationSchema) as never,
    defaultValues: {
      student: "",
      hostel: "",
      room: "",
      bed: "",
      allocated_date: new Date().toISOString().split("T")[0],
      remarks: "Annual student residential tenure",
    },
  });

  const onSubmit = (data: HostelAllocationFormData) => {
    allocateMutation.mutate(data);
  };

  const getGatePassBadge = (status: GatePassStatus) => {
    switch (status) {
      case "approved":
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Approved</span>;
      case "rejected":
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Rejected</span>;
      case "departed":
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">Out of Campus</span>;
      case "returned":
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">Checked In</span>;
      case "overdue":
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">Curfew Breach</span>;
      case "pending":
      default:
        return <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Pending Warden</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Users className="w-7 h-7 text-emerald-600" />
            {t("operations.hostelAllocationsTitle", "Hostel Allocations & Gate Passes")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.hostelAllocationsSubtitle",
              "Assign students to residential beds, manage check-out vacations, and monitor warden gate pass leaves"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsAllocateOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("operations.allocateBedBtn", "Allocate Bed")}
        </button>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-lg flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          <span className="text-sm font-medium">{feedback.message}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs underline hover:no-underline ml-4"
          >
            {t("common.dismiss", "Dismiss")}
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            type="button"
            onClick={() => setActiveTab("allocations")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "allocations"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.activeAllocationsTab", "Active Resident Allocations")} ({allocations.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("gatepasses")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "gatepasses"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.gatePassesTab", "Gate Pass Out-Leaves")} ({gatePasses.length})
          </button>
        </nav>
      </div>

      {activeTab === "allocations" ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingAllocations ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading allocations...")}</p>
            </div>
          ) : allocations.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noAllocationsFound", "No Active Resident Allocations")}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                {t("operations.noAllocationsDesc", "Allocate available hostel beds to registered students.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.residentStudent", "Student")}</th>
                    <th className="px-4 py-3">{t("operations.dormBuilding", "Dormitory & Room")}</th>
                    <th className="px-3 py-3 text-center">{t("operations.bedNo", "Bed No")}</th>
                    <th className="px-4 py-3">{t("operations.checkInDate", "Check-in Date")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                    <th className="px-5 py-3 text-right">{t("common.actions", "Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {allocations.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 font-semibold text-gray-900">
                        {item.student_name || "Student Resident"}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-700">
                        <div className="font-semibold">{item.hostel_name || "Hostel"}</div>
                        <div className="text-gray-500 font-mono">Room: {item.room}</div>
                      </td>
                      <td className="px-3 py-3 text-center whitespace-nowrap font-mono font-bold text-gray-800 text-xs">
                        {item.bed}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                        {new Date(item.allocated_date).toLocaleDateString("en-BD", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {item.is_active ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                            Active Resident
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
                            Vacated
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right">
                        {item.is_active && (
                          <button
                            type="button"
                            onClick={() => vacateMutation.mutate(item.id)}
                            className="inline-flex items-center text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-md transition"
                          >
                            <LogOut className="w-3.5 h-3.5 mr-1" />
                            Vacate Bed
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Gate Passes Table */
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingGatePasses ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading gate passes...")}</p>
            </div>
          ) : gatePasses.length === 0 ? (
            <div className="p-12 text-center">
              <DoorOpen className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noGatePassesFound", "No Gate Pass Requests on Record")}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                {t("operations.noGatePassesDesc", "Student off-campus leave requests and warden approvals will appear here.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.student", "Student")}</th>
                    <th className="px-4 py-3">{t("operations.destination", "Destination & Reason")}</th>
                    <th className="px-4 py-3">{t("operations.outTime", "Departure Time")}</th>
                    <th className="px-4 py-3">{t("operations.expectedReturn", "Expected Return")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {gatePasses.map((pass) => (
                    <tr key={pass.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 font-semibold text-gray-900">
                        {pass.student_name || "Resident Student"}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-700">
                        <div className="font-semibold flex items-center gap-1">
                          <Compass className="w-3.5 h-3.5 text-gray-400" />
                          {pass.destination}
                        </div>
                        <div className="text-gray-500 mt-0.5">{pass.reason}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                        {new Date(pass.expected_out_at).toLocaleString("en-BD", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-gray-800">
                        {new Date(pass.expected_return_at).toLocaleString("en-BD", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {getGatePassBadge(pass.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Allocate Bed Modal */}
      <Dialog open={isAllocateOpen} onOpenChange={setIsAllocateOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto p-6">
          <DialogHeader className="border-b border-gray-200 pb-3">
            <DialogTitle className="text-lg font-bold text-gray-900">
              {t("operations.allocateBedModalTitle", "Allocate Residential Bed")}
            </DialogTitle>
          </DialogHeader>

          <form
            onSubmit={(e) => {
              void handleSubmit(onSubmit)(e);
            }}
            className="space-y-4 pt-1"
          >
              <div>
                <label htmlFor="alloc_student" className="block text-xs font-semibold text-gray-700 mb-1">
                  Student ID / Registration *
                </label>
                <input
                  id="alloc_student"
                  type="text"
                  {...register("student")}
                  placeholder="e.g. STU-2026-0150"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.student && (
                  <p className="text-xs text-red-600 mt-1">{errors.student.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="alloc_hostel" className="block text-xs font-semibold text-gray-700 mb-1">
                    Hostel Building *
                  </label>
                  <input
                    id="alloc_hostel"
                    type="text"
                    {...register("hostel")}
                    placeholder="e.g. Shahid Ziaur Rahman Hall"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.hostel && (
                    <p className="text-xs text-red-600 mt-1">{errors.hostel.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="alloc_room" className="block text-xs font-semibold text-gray-700 mb-1">
                    Room Number *
                  </label>
                  <input
                    id="alloc_room"
                    type="text"
                    {...register("room")}
                    placeholder="e.g. 204"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.room && (
                    <p className="text-xs text-red-600 mt-1">{errors.room.message}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="alloc_bed" className="block text-xs font-semibold text-gray-700 mb-1">
                    Bed Number *
                  </label>
                  <input
                    id="alloc_bed"
                    type="text"
                    {...register("bed")}
                    placeholder="e.g. B-1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.bed && (
                    <p className="text-xs text-red-600 mt-1">{errors.bed.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="alloc_date" className="block text-xs font-semibold text-gray-700 mb-1">
                    Allocation Date *
                  </label>
                  <input
                    id="alloc_date"
                    type="date"
                    {...register("allocated_date")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.allocated_date && (
                    <p className="text-xs text-red-600 mt-1">{errors.allocated_date.message}</p>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAllocateOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || allocateMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || allocateMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("operations.confirmAllocation", "Confirm Allocation")}
                </button>
              </div>
            </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HostelAllocationsPage;
