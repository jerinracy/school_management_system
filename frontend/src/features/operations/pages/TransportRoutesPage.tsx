import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  MapPin,
  Plus,
  CheckCircle,
  XCircle,
} from "lucide-react";
import {
  operationsApi,
} from "../api/operationsApi";
import {
  transportRouteSchema,
  type TransportRouteFormData,
} from "../schemas/operationsSchemas";

export const TransportRoutesPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [isAddRouteOpen, setIsAddRouteOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch routes
  const { data: routesData, isLoading } = useQuery({
    queryKey: ["transport-routes"],
    queryFn: () => operationsApi.getRoutes(),
  });

  const routes = routesData?.results || [];

  // Create route mutation
  const createRouteMutation = useMutation({
    mutationFn: (data: TransportRouteFormData) => operationsApi.createRoute(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["transport-routes"] });
      setIsAddRouteOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.routeCreated", "Transport route configured successfully") });
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
  } = useForm<TransportRouteFormData>({
    resolver: zodResolver(transportRouteSchema),
    defaultValues: {
      name: "",
      code: "",
      monthly_fee: "1500.00",
      is_active: true,
    },
  });

  const onSubmit = (data: TransportRouteFormData) => {
    createRouteMutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <MapPin className="w-7 h-7 text-emerald-600" />
            {t("operations.transportRoutesTitle", "Transport Routes & Stops")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.transportRoutesSubtitle",
              "Plan route itineraries, configure pickup/drop stop points, schedules, and monthly student transit fares"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsAddRouteOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("operations.createRouteBtn", "Add New Route")}
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

      {/* Routes List */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
          <p className="text-sm">{t("common.loading", "Loading routes...")}</p>
        </div>
      ) : routes.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-base font-medium text-gray-900">
            {t("operations.noRoutesFound", "No Transport Routes Configured")}
          </h3>
          <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
            {t("operations.noRoutesDesc", "Define school bus routes and stops to enroll students into daily transportation.")}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {routes.map((route) => (
            <div
              key={route.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between hover:border-emerald-300 transition"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                    {route.code}
                  </span>
                  {route.is_active ? (
                    <span className="inline-flex items-center text-xs text-emerald-600 font-medium">
                      <CheckCircle className="w-3.5 h-3.5 mr-1" />
                      Active Route
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-xs text-gray-400 font-medium">
                      <XCircle className="w-3.5 h-3.5 mr-1" />
                      Inactive
                    </span>
                  )}
                </div>

                <h3 className="text-base font-bold text-gray-900 mb-1">{route.name}</h3>

                <div className="space-y-1.5 text-xs text-gray-600 mt-3 pt-3 border-t border-gray-100">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Vehicle:</span>
                    <span className="font-mono font-medium text-gray-800">
                      {route.vehicle_registration || "Not assigned"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Monthly Fare:</span>
                    <span className="font-bold text-gray-900 font-mono">
                      ৳{parseFloat(route.monthly_fee || "0").toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Stops preview */}
                {route.stops && route.stops.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <span className="text-[11px] font-semibold text-gray-500 uppercase block mb-1.5">
                      Stops Sequence ({route.stops.length}):
                    </span>
                    <div className="space-y-1">
                      {route.stops.slice(0, 3).map((st) => (
                        <div key={st.id} className="flex items-center justify-between text-xs text-gray-700">
                          <span className="truncate flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block" />
                            {st.name}
                          </span>
                          <span className="font-mono text-gray-400 text-[11px]">{st.pickup_time}</span>
                        </div>
                      ))}
                      {route.stops.length > 3 && (
                        <span className="text-[10px] text-gray-400 block pt-0.5">
                          +{route.stops.length - 3} more stops
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Route Modal */}
      {isAddRouteOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/10 dark:bg-black/25 backdrop-blur-sm [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] animate-data-fade flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("operations.addRouteModalTitle", "Configure New Route")}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddRouteOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleSubmit(onSubmit)(e);
              }}
              className="mt-4 space-y-4"
            >
              <div>
                <label htmlFor="route_name" className="block text-xs font-semibold text-gray-700 mb-1">
                  Route Name *
                </label>
                <input
                  id="route_name"
                  type="text"
                  {...register("name")}
                  placeholder="e.g. Uttara to Campus Morning Line"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="route_code" className="block text-xs font-semibold text-gray-700 mb-1">
                    Route Code *
                  </label>
                  <input
                    id="route_code"
                    type="text"
                    {...register("code")}
                    placeholder="e.g. RT-01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono uppercase focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.code && <p className="text-xs text-red-600 mt-1">{errors.code.message}</p>}
                </div>

                <div>
                  <label htmlFor="route_fee" className="block text-xs font-semibold text-gray-700 mb-1">
                    Monthly Fare (৳) *
                  </label>
                  <input
                    id="route_fee"
                    type="text"
                    {...register("monthly_fee")}
                    placeholder="e.g. 1500.00"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                  />
                  {errors.monthly_fee && (
                    <p className="text-xs text-red-600 mt-1">{errors.monthly_fee.message}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="route_active"
                  {...register("is_active")}
                  className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
                />
                <label htmlFor="route_active" className="ml-2 block text-xs font-medium text-gray-700">
                  Activate route for student transit assignment
                </label>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddRouteOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || createRouteMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || createRouteMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("common.create", "Save Route")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransportRoutesPage;
