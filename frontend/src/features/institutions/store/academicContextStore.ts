import { create } from "zustand";
import { persist } from "zustand/middleware";
import { queryClient } from "@/lib/query-client";
import {
  institutionApi,
  type AcademicSession,
  type Branch,
  type Shift,
} from "../api/institutionApi";

interface AcademicContextState {
  branches: Branch[];
  selectedBranchId: string | null;
  selectedBranch: Branch | null;

  sessions: AcademicSession[];
  selectedSessionId: string | null;
  selectedSession: AcademicSession | null;

  shifts: Shift[];
  selectedShiftId: string | null;
  selectedShift: Shift | null;

  isLoading: boolean;
  error: string | null;

  fetchContext: (force?: boolean) => Promise<void>;
  setSelectedBranchId: (id: string) => void;
  setSelectedSessionId: (id: string) => void;
  setSelectedShiftId: (id: string) => void;
}

export const useAcademicContextStore = create<AcademicContextState>()(
  persist(
    (set, get) => ({
      branches: [],
      selectedBranchId: null,
      selectedBranch: null,

      sessions: [],
      selectedSessionId: null,
      selectedSession: null,

      shifts: [],
      selectedShiftId: null,
      selectedShift: null,

      isLoading: false,
      error: null,

      fetchContext: async (force = false) => {
        const state = get();
        if (
          !force &&
          state.branches.length > 0 &&
          state.sessions.length > 0 &&
          state.shifts.length > 0
        ) {
          return;
        }

        set({ isLoading: true, error: null });
        try {
          const [branches, sessions, shifts] = await Promise.all([
            institutionApi.getBranches().catch(() => [] as Branch[]),
            institutionApi.getSessions().catch(() => [] as AcademicSession[]),
            institutionApi.getShifts().catch(() => [] as Shift[]),
          ]);

          const currentBranchId = get().selectedBranchId;
          const matchedBranch =
            branches.find((b) => b.id === currentBranchId) ||
            branches.find((b) => b.is_main) ||
            branches[0] ||
            null;

          const currentSessionId = get().selectedSessionId;
          const matchedSession =
            sessions.find((s) => s.id === currentSessionId) ||
            sessions.find((s) => s.is_current) ||
            sessions[0] ||
            null;

          const currentShiftId = get().selectedShiftId;
          const matchedShift =
            shifts.find((s) => s.id === currentShiftId) || shifts[0] || null;

          set({
            branches,
            selectedBranch: matchedBranch,
            selectedBranchId: matchedBranch ? matchedBranch.id : null,

            sessions,
            selectedSession: matchedSession,
            selectedSessionId: matchedSession ? matchedSession.id : null,

            shifts,
            selectedShift: matchedShift,
            selectedShiftId: matchedShift ? matchedShift.id : null,

            isLoading: false,
          });
        } catch (err: unknown) {
          set({
            isLoading: false,
            error: err instanceof Error ? err.message : "Failed to load academic context",
          });
        }
      },

      setSelectedBranchId: (id: string) => {
        const branch = get().branches.find((b) => b.id === id) || null;
        set({ selectedBranchId: id, selectedBranch: branch });
      },

      setSelectedSessionId: (id: string) => {
        const session = get().sessions.find((s) => s.id === id) || null;
        set({ selectedSessionId: id, selectedSession: session });
        void queryClient.invalidateQueries();
      },

      setSelectedShiftId: (id: string) => {
        const shift = get().shifts.find((s) => s.id === id) || null;
        set({ selectedShiftId: id, selectedShift: shift });
      },
    }),
    {
      name: "sms_academic_context",
      partialize: (state) => ({
        selectedBranchId: state.selectedBranchId,
        selectedSessionId: state.selectedSessionId,
        selectedShiftId: state.selectedShiftId,
      }),
    },
  ),
);
