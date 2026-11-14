import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { staffApi } from "@/features/staff/api/staffApi";
import {
  staffCreateSchema,
  type StaffCreateFormData,
} from "@/features/staff/schemas/staffSchemas";

export function StaffCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<StaffCreateFormData>({
    resolver: zodResolver(staffCreateSchema) as never,
    defaultValues: {
      full_name_en: "",
      full_name_bn: "",
      phone: "",
      alt_phone: "",
      email: "",
      dob: "",
      gender: "male",
      blood_group: "",
      nid: "",
      department: "",
      designation: "",
      staff_type: "teacher",
      joining_date: new Date().toISOString().split("T")[0] ?? "2026-01-01",
      tin_number: "",
      is_mpo: false,
      mpo_index_number: "",
      present_address: "",
      permanent_address: "",
      emergency_contact_name: "",
      emergency_contact_phone: "",
      emergency_contact_relation: "Spouse",
    },
  });

  const isMpo = form.watch("is_mpo");

  // Options Queries
  const { data: departmentsData } = useQuery({
    queryKey: ["staff-departments"],
    queryFn: () => staffApi.getDepartments(),
  });

  const { data: designationsData } = useQuery({
    queryKey: ["staff-designations"],
    queryFn: () => staffApi.getDesignations(),
  });

  const departments = departmentsData?.results ?? [];
  const designations = designationsData?.results ?? [];

  const onSubmit = async (data: StaffCreateFormData) => {
    setSubmitError(null);
    try {
      const staff = await staffApi.createStaff({
        full_name_en: data.full_name_en,
        full_name_bn: data.full_name_bn,
        phone: data.phone,
        alt_phone: data.alt_phone || undefined,
        email: data.email || undefined,
        dob: data.dob,
        gender: data.gender,
        blood_group: data.blood_group || undefined,
        nid: data.nid || undefined,
        department: data.department,
        designation: data.designation,
        staff_type: data.staff_type,
        joining_date: data.joining_date,
        tin_number: data.tin_number || undefined,
        is_mpo: data.is_mpo,
        mpo_index_number: data.is_mpo ? data.mpo_index_number || undefined : undefined,
        present_address: data.present_address,
        permanent_address: data.permanent_address || undefined,
        emergency_contact_name: data.emergency_contact_name,
        emergency_contact_phone: data.emergency_contact_phone,
        emergency_contact_relation: data.emergency_contact_relation || undefined,
      });

      void navigate(`/staff/${staff.id}`);
    } catch (err: unknown) {
      setSubmitError((err as Error).message || "Failed to create employee profile.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Return to Roster */}
      <div className="flex items-center justify-between">
        <Link
          to="/staff"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-emerald-800 dark:hover:text-emerald-400 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>{t("staff.backToRoster", "Back to Staff Roster")}</span>
        </Link>
        <span className="text-xs font-mono text-slate-400">
          {t("staff.onboardingPortal", "Institutional Employee Onboarding")}
        </span>
      </div>

      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          {t("staff.onboardingTitle", "Add New Staff Member")}
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          {t(
            "staff.onboardingSubtitle",
            "Register employee demographics, appointment scale, designation, and emergency contacts.",
          )}
        </p>
      </div>

      {submitError && (
        <div className="rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs text-danger font-medium">
          {submitError}
        </div>
      )}

      <form
        onSubmit={(e) => {
          void form.handleSubmit(onSubmit as never)(e);
        }}
        className="space-y-6"
      >
        {/* Section 1: Demographics */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("staff.demographicsSection", "1. Demographic Information")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.nameEn", "Full Name (English)")}
              </FormLabel>
              <Input
                placeholder="e.g. Mohammad Rafiqul Islam"
                className="h-9 text-xs rounded-lg"
                {...form.register("full_name_en")}
              />
              {form.formState.errors.full_name_en && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.full_name_en.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.nameBn", "Full Name (Bangla)")}
              </FormLabel>
              <Input
                placeholder="e.g. মোহাম্মদ রফিকুল ইসলাম"
                className="h-9 text-xs rounded-lg"
                {...form.register("full_name_bn")}
              />
              {form.formState.errors.full_name_bn && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.full_name_bn.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.dob", "Date of Birth")}
              </FormLabel>
              <Input
                type="date"
                className="h-9 text-xs rounded-lg font-mono"
                {...form.register("dob")}
              />
              {form.formState.errors.dob && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.dob.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.gender", "Gender")}
              </FormLabel>
              <Controller
                control={form.control}
                name="gender"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-9 text-xs rounded-lg">
                      <SelectValue placeholder="Select Gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male" className="text-xs">{t("gender.male", "Male")}</SelectItem>
                      <SelectItem value="female" className="text-xs">{t("gender.female", "Female")}</SelectItem>
                      <SelectItem value="other" className="text-xs">{t("gender.other", "Other")}</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("students.bloodGroup", "Blood Group")}
              </FormLabel>
              <Controller
                control={form.control}
                name="blood_group"
                render={({ field }) => (
                  <Select value={field.value || ""} onValueChange={field.onChange}>
                    <SelectTrigger className="h-9 text-xs rounded-lg">
                      <SelectValue placeholder="Select Blood Group" />
                    </SelectTrigger>
                    <SelectContent>
                      {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                        <SelectItem key={bg} value={bg} className="text-xs font-mono">
                          {bg}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <FormField className="sm:col-span-2">
              <FormLabel className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.nid", "National ID (10, 13, or 17 Digits)")}
              </FormLabel>
              <Input
                placeholder="e.g. 19851234567890123"
                className="h-9 text-xs font-mono rounded-lg"
                {...form.register("nid")}
              />
              {form.formState.errors.nid && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.nid.message ?? "")}
                </p>
              )}
            </FormField>
          </div>
        </div>

        {/* Section 2: Employment & Designation Details */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("staff.employmentSection", "2. Institutional Appointment & Designation")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.staffType", "Staff Role Type")}
              </FormLabel>
              <Controller
                control={form.control}
                name="staff_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-9 text-xs rounded-lg">
                      <SelectValue placeholder="Select Staff Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="teacher" className="text-xs">Teacher</SelectItem>
                      <SelectItem value="admin" className="text-xs">Administration</SelectItem>
                      <SelectItem value="support" className="text-xs">Support Staff</SelectItem>
                      <SelectItem value="driver" className="text-xs">Driver</SelectItem>
                      <SelectItem value="security" className="text-xs">Security</SelectItem>
                      <SelectItem value="other" className="text-xs">Other</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.joiningDate", "Date of Joining")}
              </FormLabel>
              <Input
                type="date"
                className="h-9 text-xs rounded-lg font-mono"
                {...form.register("joining_date")}
              />
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.department", "Department")}
              </FormLabel>
              <Controller
                control={form.control}
                name="department"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-9 text-xs rounded-lg">
                      <SelectValue placeholder="Select Department" />
                    </SelectTrigger>
                    <SelectContent>
                      {departments.map((d) => (
                        <SelectItem key={d.id} value={d.id} className="text-xs">
                          {d.name} ({d.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.department && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.department.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.designation", "Designation")}
              </FormLabel>
              <Controller
                control={form.control}
                name="designation"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-9 text-xs rounded-lg">
                      <SelectValue placeholder="Select Designation" />
                    </SelectTrigger>
                    <SelectContent>
                      {designations.map((des) => (
                        <SelectItem key={des.id} value={des.id} className="text-xs">
                          {des.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.designation && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.designation.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.tinNumber", "TIN Number (Taxpayer ID)")}
              </FormLabel>
              <Input
                placeholder="e.g. 123456789012"
                className="h-9 text-xs font-mono rounded-lg"
                {...form.register("tin_number")}
              />
            </FormField>

            <div className="sm:col-span-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_mpo"
                  className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-600"
                  {...form.register("is_mpo")}
                />
                <label htmlFor="is_mpo" className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  {t("staff.isMpoEmployee", "MPO Enlisted Employee (Monthly Pay Order)")}
                </label>
              </div>

              {isMpo && (
                <div className="mt-3 pl-7 max-w-sm">
                  <FormLabel className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    {t("staff.mpoIndex", "MPO Index Number")}
                  </FormLabel>
                  <Input
                    placeholder="e.g. N-1029384"
                    className="h-9 text-xs font-mono rounded-lg mt-1"
                    {...form.register("mpo_index_number")}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 3: Contact & Emergency Details */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("staff.contactSection", "3. Contact & Emergency Details")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.primaryPhone", "Primary Mobile Number")}
              </FormLabel>
              <Input
                placeholder="+8801XXXXXXXXX"
                className="h-9 text-xs font-mono rounded-lg"
                {...form.register("phone")}
              />
              {form.formState.errors.phone && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.phone.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.email", "Official / Personal Email")}
              </FormLabel>
              <Input
                type="email"
                placeholder="teacher@school.edu.bd"
                className="h-9 text-xs font-mono rounded-lg"
                {...form.register("email")}
              />
            </FormField>

            <FormField className="sm:col-span-2">
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.presentAddress", "Present Address")}
              </FormLabel>
              <Input
                placeholder="House, Road, Area, Thana, District"
                className="h-9 text-xs rounded-lg"
                {...form.register("present_address")}
              />
              {form.formState.errors.present_address && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.present_address.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.emergencyContactName", "Emergency Contact Name")}
              </FormLabel>
              <Input
                placeholder="Contact Person Full Name"
                className="h-9 text-xs rounded-lg"
                {...form.register("emergency_contact_name")}
              />
              {form.formState.errors.emergency_contact_name && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.emergency_contact_name.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {t("staff.emergencyContactPhone", "Emergency Contact Mobile")}
              </FormLabel>
              <Input
                placeholder="+8801XXXXXXXXX"
                className="h-9 text-xs font-mono rounded-lg"
                {...form.register("emergency_contact_phone")}
              />
              {form.formState.errors.emergency_contact_phone && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.emergency_contact_phone.message ?? "")}
                </p>
              )}
            </FormField>
          </div>
        </div>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              void navigate("/staff");
            }}
            className="text-xs rounded-lg"
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="text-xs font-semibold bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg px-6"
          >
            {form.formState.isSubmitting
              ? t("common.saving", "Saving...")
              : t("staff.saveEmployee", "Save Employee Profile")}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default StaffCreatePage;
