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
import { studentsApi } from "@/features/students/api/studentsApi";
import { academicApi } from "@/features/academics/api/academicApi";
import { institutionApi } from "@/features/institutions/api/institutionApi";
import {
  studentCreateSchema,
  type StudentCreateFormData,
} from "@/features/students/schemas/studentSchemas";

export function StudentCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<StudentCreateFormData>({
    resolver: zodResolver(studentCreateSchema) as never,
    defaultValues: {
      name_en: "",
      name_bn: "",
      dob: "",
      gender: "male",
      blood_group: "",
      religion: "islam",
      birth_reg_no: "",
      present_address: "",
      emergency_contact_name: "",
      emergency_contact_phone: "",
      session_id: "",
      class_level_id: "",
      section_id: "",
      roll_no: 1,
    },
  });

  const selectedClassId = form.watch("class_level_id");

  // Options Queries
  const { data: sessions = [] } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => institutionApi.getSessions(),
  });

  const { data: classes = [] } = useQuery({
    queryKey: ["classes"],
    queryFn: () => academicApi.getClasses(),
  });

  const { data: sections = [] } = useQuery({
    queryKey: ["sections", selectedClassId],
    queryFn: () => academicApi.getSections(selectedClassId),
    enabled: Boolean(selectedClassId),
  });

  const onSubmit = async (data: StudentCreateFormData) => {
    setSubmitError(null);
    try {
      // 1. Create Student Demographic Profile
      const student = await studentsApi.createStudent({
        name_en: data.name_en,
        name_bn: data.name_bn,
        dob: data.dob,
        gender: data.gender,
        blood_group: data.blood_group || undefined,
        religion: data.religion,
        birth_reg_no: data.birth_reg_no || undefined,
        present_address: data.present_address,
        admission_date: new Date().toISOString().split("T")[0] ?? "2026-01-01",
        emergency_contact_name: data.emergency_contact_name,
        emergency_contact_phone: data.emergency_contact_phone,
      });

      // 2. Create Initial Active Enrollment
      await studentsApi.createEnrollment({
        student: student.id,
        session: data.session_id,
        class_level: data.class_level_id,
        section: data.section_id,
        roll_no: Number(data.roll_no),
        status: "active",
      });

      void navigate(`/students/${student.id}`);
    } catch (err) {
      setSubmitError((err as Error).message || "Failed to create student.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Return to Roster */}
      <div>
        <Link
          to="/students"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{t("students.backToDirectory", "Back to Student Directory")}</span>
        </Link>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          {t("students.newStudentAdmission", "New Student Admission")}
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500">
          {t("students.newStudentSubtitle", "Register demographic information and assign initial class placement.")}
        </p>
      </div>

      {submitError && (
        <div className="rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs text-danger font-medium">
          {submitError}
        </div>
      )}

      <form onSubmit={(e) => { void form.handleSubmit(onSubmit as never)(e); }} className="space-y-6">
        {/* Section 1: Demographics */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("students.demographicsSection", "1. Demographic Information")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.nameEn", "Full Name (English)")}
              </FormLabel>
              <Input
                placeholder="e.g. Tanvir Ahmed"
                className="h-10 text-xs rounded-lg"
                {...form.register("name_en")}
              />
              {form.formState.errors.name_en && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.name_en.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.nameBn", "Full Name (Bangla)")}
              </FormLabel>
              <Input
                placeholder="e.g. তানভীর আহমেদ"
                className="h-10 text-xs rounded-lg"
                {...form.register("name_bn")}
              />
              {form.formState.errors.name_bn && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.name_bn.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.dob", "Date of Birth")}
              </FormLabel>
              <Input
                type="date"
                className="h-10 text-xs rounded-lg"
                {...form.register("dob")}
              />
              {form.formState.errors.dob && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.dob.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.gender", "Gender")}
              </FormLabel>
              <Controller
                control={form.control}
                name="gender"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male" className="text-xs">{t("students.male", "Male")}</SelectItem>
                      <SelectItem value="female" className="text-xs">{t("students.female", "Female")}</SelectItem>
                      <SelectItem value="other" className="text-xs">{t("students.other", "Other")}</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <FormField>
              <FormLabel className="text-xs font-medium text-slate-700">
                {t("students.bloodGroup", "Blood Group")}
              </FormLabel>
              <Controller
                control={form.control}
                name="blood_group"
                render={({ field }) => (
                  <Select value={field.value || ""} onValueChange={field.onChange}>
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue placeholder={t("students.selectBloodGroup", "Select Blood Group")} />
                    </SelectTrigger>
                    <SelectContent>
                      {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                        <SelectItem key={bg} value={bg} className="text-xs">{bg}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.religion", "Religion")}
              </FormLabel>
              <Controller
                control={form.control}
                name="religion"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="islam" className="text-xs">Islam</SelectItem>
                      <SelectItem value="hinduism" className="text-xs">Hinduism</SelectItem>
                      <SelectItem value="buddhism" className="text-xs">Buddhism</SelectItem>
                      <SelectItem value="christianity" className="text-xs">Christianity</SelectItem>
                      <SelectItem value="other" className="text-xs">Other</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>

            <div className="sm:col-span-2">
              <FormField>
                <FormLabel className="text-xs font-medium text-slate-700">
                  {t("students.birthRegNo", "Birth Registration Certificate Number (17 Digits)")}
                </FormLabel>
                <Input
                  maxLength={17}
                  placeholder="e.g. 20121234567890123"
                  className="h-10 text-xs font-mono rounded-lg"
                  {...form.register("birth_reg_no")}
                />
                {form.formState.errors.birth_reg_no && (
                  <p className="text-xs text-danger mt-1">
                    {t(form.formState.errors.birth_reg_no.message ?? "")}
                  </p>
                )}
              </FormField>
            </div>
          </div>
        </div>

        {/* Section 2: Contact Details */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("students.contactSection", "2. Address & Emergency Contacts")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <FormField>
                <FormLabel required className="text-xs font-medium text-slate-700">
                  {t("students.presentAddress", "Present Address")}
                </FormLabel>
                <Input
                  placeholder="House, Road, Area, Thana, District"
                  className="h-10 text-xs rounded-lg"
                  {...form.register("present_address")}
                />
                {form.formState.errors.present_address && (
                  <p className="text-xs text-danger mt-1">
                    {t(form.formState.errors.present_address.message ?? "")}
                  </p>
                )}
              </FormField>
            </div>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.emergencyContactName", "Emergency Contact Person")}
              </FormLabel>
              <Input
                placeholder="Parent or Guardian Name"
                className="h-10 text-xs rounded-lg"
                {...form.register("emergency_contact_name")}
              />
              {form.formState.errors.emergency_contact_name && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.emergency_contact_name.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.emergencyContactPhone", "Emergency Mobile Number")}
              </FormLabel>
              <Input
                placeholder="+8801XXXXXXXXX"
                className="h-10 text-xs font-mono rounded-lg"
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

        {/* Section 3: Academic Placement */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-2xs space-y-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-2">
            {t("students.placementSection", "3. Initial Academic Enrollment")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("institutions.session", "Academic Session")}
              </FormLabel>
              <Controller
                control={form.control}
                name="session_id"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue placeholder={t("institutions.selectSession", "Select Session")} />
                    </SelectTrigger>
                    <SelectContent>
                      {sessions.map((s) => (
                        <SelectItem key={s.id} value={s.id} className="text-xs">
                          {s.name} {s.is_current ? `(${t("common.current", "Current")})` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.session_id && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.session_id.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("academics.class", "Class Grade")}
              </FormLabel>
              <Controller
                control={form.control}
                name="class_level_id"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={(val) => {
                      field.onChange(val);
                      form.setValue("section_id", "");
                    }}
                  >
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue placeholder={t("academics.selectClass", "Select Class")} />
                    </SelectTrigger>
                    <SelectContent>
                      {classes.map((c) => (
                        <SelectItem key={c.id} value={c.id} className="text-xs">
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.class_level_id && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.class_level_id.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("academics.section", "Section")}
              </FormLabel>
              <Controller
                control={form.control}
                name="section_id"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={!selectedClassId}
                  >
                    <SelectTrigger className="h-10 text-xs rounded-lg">
                      <SelectValue placeholder={t("academics.selectSection", "Select Section")} />
                    </SelectTrigger>
                    <SelectContent>
                      {sections.map((sec) => (
                        <SelectItem key={sec.id} value={sec.id} className="text-xs">
                          {sec.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.section_id && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.section_id.message ?? "")}
                </p>
              )}
            </FormField>

            <FormField>
              <FormLabel required className="text-xs font-medium text-slate-700">
                {t("students.rollNo", "Class Roll Number")}
              </FormLabel>
              <Input
                type="number"
                min={1}
                className="h-10 text-xs font-mono rounded-lg"
                {...form.register("roll_no")}
              />
              {form.formState.errors.roll_no && (
                <p className="text-xs text-danger mt-1">
                  {t(form.formState.errors.roll_no.message ?? "")}
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
              void navigate("/students");
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
              : t("students.saveAndAdmit", "Admit Student")}
          </Button>
        </div>
      </form>
    </div>
  );
}
