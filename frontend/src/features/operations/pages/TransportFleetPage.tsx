import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bus,
  Plus,
  CheckCircle,
  AlertTriangle,
  User,
  Phone,
  ShieldAlert,
} from "lucide-react";
import {
  operationsApi,
  type VehicleStatus,
} from "../api/operationsApi";
import {
  vehicleSchema,
  type VehicleFormData,
} from "../schemas/operationsSchemas";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export const TransportFleetPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"vehicles" | "drivers">("vehicles");
  const [isAddVehicleOpen, setIsAddVehicleOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch vehicles
  const { data: vehiclesData, isLoading: isLoadingVehicles } = useQuery({
    queryKey: ["transport-vehicles"],
    queryFn: () => operationsApi.getVehicles(),
  });

  const vehicles = vehiclesData?.results || [];

  // Fetch drivers
  const { data: driversData, isLoading: isLoadingDrivers } = useQuery({
    queryKey: ["transport-drivers"],
    queryFn: () => operationsApi.getDrivers(),
  });

  const drivers = driversData?.results || [];

  // Create vehicle mutation
  const createVehicleMutation = useMutation({
    mutationFn: (data: VehicleFormData) => operationsApi.createVehicle(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["transport-vehicles"] });
      setIsAddVehicleOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.vehicleAdded", "Vehicle registered successfully") });
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
  } = useForm<VehicleFormData>({
    resolver: zodResolver(vehicleSchema) as never,
    defaultValues: {
      registration_no: "",
      vehicle_type: "bus",
      capacity: 40,
      make_model: "Hino AK1J",
      fitness_expiry: new Date(Date.now() + 86400000 * 180).toISOString().split("T")[0],
      tax_token_expiry: new Date(Date.now() + 86400000 * 180).toISOString().split("T")[0],
      status: "active",
    },
  });

  const onSubmit = (data: VehicleFormData) => {
    createVehicleMutation.mutate(data);
  };

  const isExpiredOrWarning = (expiryDate?: string | null) => {
    if (!expiryDate) return false;
    const diffDays = Math.ceil((new Date(expiryDate).getTime() - Date.now()) / (1000 * 3600 * 24));
    return diffDays < 30;
  };

  const getStatusBadge = (status: VehicleStatus) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle className="w-3.5 h-3.5 mr-1" />
            Active
          </span>
        );
      case "maintenance":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            In Maintenance
          </span>
        );
      case "inactive":
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            Inactive
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Bus className="w-7 h-7 text-emerald-600" />
            {t("operations.transportFleetTitle", "Transport Fleet & Vehicles")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.transportFleetSubtitle",
              "Manage school buses, vans, BRTA fitness compliance, tax token renewals, and driver credentials"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsAddVehicleOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("operations.addVehicleBtn", "Add Vehicle")}
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
            onClick={() => setActiveTab("vehicles")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "vehicles"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.vehiclesTab", "Fleet Inventory")} ({vehicles.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("drivers")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "drivers"
                ? "border-emerald-600 text-emerald-700 font-bold"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t("operations.driversTab", "Drivers & Helpers Roster")} ({drivers.length})
          </button>
        </nav>
      </div>

      {activeTab === "vehicles" ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingVehicles ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading vehicle roster...")}</p>
            </div>
          ) : vehicles.length === 0 ? (
            <div className="p-12 text-center">
              <Bus className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noVehiclesFound", "No Vehicles in Fleet")}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                {t("operations.noVehiclesDesc", "Add school buses and passenger vans to configure transportation routes.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.vehicleReg", "Registration No & Model")}</th>
                    <th className="px-4 py-3">{t("operations.type", "Type")}</th>
                    <th className="px-3 py-3 text-center">{t("operations.capacity", "Capacity")}</th>
                    <th className="px-4 py-3">{t("operations.fitnessExpiry", "BRTA Fitness")}</th>
                    <th className="px-4 py-3">{t("operations.taxExpiry", "Tax Token")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {vehicles.map((v) => {
                    const fitnessAlert = isExpiredOrWarning(v.fitness_expiry);
                    const taxAlert = isExpiredOrWarning(v.tax_token_expiry);

                    return (
                      <tr key={v.id} className="hover:bg-gray-50/75 transition">
                        <td className="px-5 py-3 whitespace-nowrap">
                          <div className="font-mono font-bold text-gray-900">{v.registration_no}</div>
                          <div className="text-xs text-gray-500">{v.make_model || "Standard Bus"}</div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs font-semibold capitalize text-gray-700">
                          {v.vehicle_type}
                        </td>
                        <td className="px-3 py-3 text-center whitespace-nowrap font-mono font-bold text-gray-900 text-xs">
                          {v.capacity} seats
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded font-mono ${
                              fitnessAlert ? "bg-red-100 text-red-800 font-bold" : "text-gray-700"
                            }`}
                          >
                            {fitnessAlert && <ShieldAlert className="w-3 h-3 mr-1 text-red-600" />}
                            {v.fitness_expiry || "N/A"}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded font-mono ${
                              taxAlert ? "bg-red-100 text-red-800 font-bold" : "text-gray-700"
                            }`}
                          >
                            {taxAlert && <ShieldAlert className="w-3 h-3 mr-1 text-red-600" />}
                            {v.tax_token_expiry || "N/A"}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {getStatusBadge(v.status)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Drivers Roster */
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoadingDrivers ? (
            <div className="p-12 text-center text-gray-500">
              <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
              <p className="text-sm">{t("common.loading", "Loading drivers...")}</p>
            </div>
          ) : drivers.length === 0 ? (
            <div className="p-12 text-center">
              <User className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-medium text-gray-900">
                {t("operations.noDriversFound", "No Drivers Enrolled")}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                {t("operations.noDriversDesc", "Enroll drivers and assign them to active school routes.")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">{t("operations.driverName", "Driver Name")}</th>
                    <th className="px-4 py-3">{t("operations.licenseNo", "Driving License")}</th>
                    <th className="px-4 py-3">{t("operations.helper", "Helper & Contact")}</th>
                    <th className="px-4 py-3">{t("operations.status", "Status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {drivers.map((d) => (
                    <tr key={d.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-5 py-3 font-semibold text-gray-900">
                        {d.staff_name || "School Driver"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-800">
                        <div>{d.license_no}</div>
                        <div className="text-gray-400 text-[11px]">Exp: {d.license_expiry || "N/A"}</div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-700">
                        <div>{d.helper_name || "—"}</div>
                        {d.helper_phone && (
                          <div className="text-gray-500 font-mono flex items-center gap-1 mt-0.5">
                            <Phone className="w-3 h-3 text-gray-400" />
                            {d.helper_phone}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 capitalize">
                          {d.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Add Vehicle Modal */}
      <Dialog open={isAddVehicleOpen} onOpenChange={setIsAddVehicleOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto p-6">
          <DialogHeader className="border-b border-gray-200 pb-3">
            <DialogTitle className="text-lg font-bold text-gray-900">
              {t("operations.addVehicleModalTitle", "Add Vehicle to Fleet")}
            </DialogTitle>
          </DialogHeader>

          <form
            onSubmit={(e) => {
              void handleSubmit(onSubmit)(e);
            }}
            className="space-y-4 pt-1"
          >
              <div>
                <label htmlFor="veh_reg" className="block text-xs font-semibold text-gray-700 mb-1">
                  BRTA Registration Number *
                </label>
                <input
                  id="veh_reg"
                  type="text"
                  {...register("registration_no")}
                  placeholder="e.g. Dhaka Metro-Cha 11-4521"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.registration_no && (
                  <p className="text-xs text-red-600 mt-1">{errors.registration_no.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="veh_type" className="block text-xs font-semibold text-gray-700 mb-1">
                    Vehicle Type *
                  </label>
                  <select
                    id="veh_type"
                    {...register("vehicle_type")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  >
                    <option value="bus">School Bus</option>
                    <option value="minibus">Minibus / Coaster</option>
                    <option value="van">Passenger Van</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="veh_capacity" className="block text-xs font-semibold text-gray-700 mb-1">
                    Seating Capacity *
                  </label>
                  <input
                    id="veh_capacity"
                    type="number"
                    {...register("capacity")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.capacity && (
                    <p className="text-xs text-red-600 mt-1">{errors.capacity.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="veh_model" className="block text-xs font-semibold text-gray-700 mb-1">
                  Make & Model
                </label>
                <input
                  id="veh_model"
                  type="text"
                  {...register("make_model")}
                  placeholder="e.g. Eicher 10.75 Starline"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="veh_fitness" className="block text-xs font-semibold text-gray-700 mb-1">
                    Fitness Certificate Expiry
                  </label>
                  <input
                    id="veh_fitness"
                    type="date"
                    {...register("fitness_expiry")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label htmlFor="veh_tax" className="block text-xs font-semibold text-gray-700 mb-1">
                    Tax Token Expiry
                  </label>
                  <input
                    id="veh_tax"
                    type="date"
                    {...register("tax_token_expiry")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddVehicleOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || createVehicleMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || createVehicleMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("common.create", "Save Vehicle")}
                </button>
              </div>
            </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TransportFleetPage;
