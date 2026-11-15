import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Building,
  Clock,
  Layers,
} from "lucide-react";
import {
  operationsApi,
  type BedStatus,
} from "../api/operationsApi";

export const HostelDormsPage: React.FC = () => {
  const { t } = useTranslation();

  const [selectedHostelId, setSelectedHostelId] = useState<string>("all");

  // Fetch hostels
  const { data: hostelsData, isLoading: isLoadingHostels } = useQuery({
    queryKey: ["hostels-list"],
    queryFn: () => operationsApi.getHostels(),
  });

  const hostels = hostelsData?.results || [];

  // Fetch rooms
  const { data: roomsData, isLoading: isLoadingRooms } = useQuery({
    queryKey: ["hostel-rooms", selectedHostelId],
    queryFn: () =>
      operationsApi.getHostelRooms({
        hostel: selectedHostelId !== "all" ? selectedHostelId : undefined,
      }),
  });

  const rooms = roomsData?.results || [];

  // Fetch beds
  const { data: bedsData } = useQuery({
    queryKey: ["hostel-beds"],
    queryFn: () => operationsApi.getBeds(),
  });

  const beds = bedsData?.results || [];

  const getBedStatusBadge = (status: BedStatus) => {
    switch (status) {
      case "available":
        return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Free</span>;
      case "occupied":
        return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">Occupied</span>;
      case "reserved":
        return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Reserved</span>;
      case "maintenance":
      default:
        return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">Under Maint.</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Building className="w-7 h-7 text-emerald-600" />
            {t("operations.hostelDormsTitle", "Hostel Dormitories & Bed Matrix")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.hostelDormsSubtitle",
              "Manage residential buildings, room floors, curfew schedules, and live bed occupancy statuses"
            )}
          </p>
        </div>
      </div>

      {/* Buildings Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {isLoadingHostels ? (
          <div className="col-span-full p-8 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading dormitories...")}</p>
          </div>
        ) : hostels.length === 0 ? (
          <div className="col-span-full p-8 text-center border rounded-xl bg-white">
            <Building className="w-12 h-12 text-gray-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-gray-800">No hostel buildings configured</p>
          </div>
        ) : (
          hostels.map((h) => (
            <button
              type="button"
              key={h.id}
              className={`w-full text-left p-5 rounded-xl border transition shadow-sm bg-white cursor-pointer ${
                selectedHostelId === h.id ? "border-emerald-500 ring-2 ring-emerald-500/20" : "border-gray-200 hover:border-gray-300"
              }`}
              onClick={() => setSelectedHostelId(selectedHostelId === h.id ? "all" : h.id)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  {h.code}
                </span>
                <span className="text-xs font-semibold capitalize px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                  {h.hostel_type} Hostel
                </span>
              </div>
              <h3 className="text-base font-bold text-gray-900">{h.name}</h3>
              {h.address && <p className="text-xs text-gray-500 mt-0.5">{h.address}</p>}

              <div className="flex items-center justify-between text-xs text-gray-600 mt-4 pt-3 border-t border-gray-100">
                <span className="flex items-center gap-1 font-medium">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  Curfew: {h.curfew_time || "21:00"}
                </span>
                <span className="text-emerald-700 font-semibold">
                  {selectedHostelId === h.id ? "Selected Filter" : "Click to Filter"}
                </span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Rooms & Beds Occupancy Grid */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-emerald-600" />
              {t("operations.roomsTitle", "Rooms & Live Bed Occupancy Matrix")}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Visual bed status across dormitory floors
            </p>
          </div>
          {selectedHostelId !== "all" && (
            <button
              type="button"
              onClick={() => setSelectedHostelId("all")}
              className="text-xs font-medium text-emerald-600 hover:text-emerald-700"
            >
              Reset filter (Show all buildings)
            </button>
          )}
        </div>

        {isLoadingRooms ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            {t("common.loading", "Loading room matrix...")}
          </div>
        ) : rooms.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No rooms found for selected building.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rooms.map((room) => {
              const roomBeds = beds.filter((b) => b.room === room.id);

              return (
                <div key={room.id} className="p-4 rounded-xl border border-gray-200 bg-gray-50/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-base font-bold text-gray-900">Room {room.room_number}</span>
                      <span className="text-xs text-gray-500 ml-2">Floor {room.floor}</span>
                    </div>
                    <span className="font-mono text-xs font-bold text-gray-900">
                      ৳{parseFloat(room.monthly_fee || "0").toFixed(0)}/mo
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] font-semibold text-gray-500 uppercase block mb-1">
                      Beds ({roomBeds.length || room.capacity}):
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                      {roomBeds.length > 0 ? (
                        roomBeds.map((bed) => (
                          <div
                            key={bed.id}
                            className="p-2 bg-white rounded-lg border border-gray-200 flex items-center justify-between"
                          >
                            <span className="text-xs font-mono font-medium text-gray-800">
                              Bed {bed.bed_number}
                            </span>
                            {getBedStatusBadge(bed.status)}
                          </div>
                        ))
                      ) : (
                        Array.from({ length: room.capacity }).map((_, idx) => (
                          <div
                            key={idx}
                            className="p-2 bg-white rounded-lg border border-gray-200 flex items-center justify-between"
                          >
                            <span className="text-xs font-mono font-medium text-gray-800">
                              Bed {idx + 1}
                            </span>
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              Free
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default HostelDormsPage;
