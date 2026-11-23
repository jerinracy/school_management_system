import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { UserCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField, FormLabel } from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { studentsApi, type StudentDetail, type StudentListItem } from "@/features/students/api/studentsApi";

interface EditStudentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  student: StudentDetail | StudentListItem | null;
  onSuccess?: () => void;
}

export function EditStudentDialog({
  open,
  onOpenChange,
  student,
  onSuccess,
}: EditStudentDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"general" | "contact" | "special">("general");

  // Form State
  const [nameEn, setNameEn] = useState("");
  const [nameBn, setNameBn] = useState("");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("male");
  const [bloodGroup, setBloodGroup] = useState("");
  const [religion, setReligion] = useState("islam");
  const [status, setStatus] = useState("active");
  const [admissionDate, setAdmissionDate] = useState("");

  const [phone, setPhone] = useState("");
  const [birthRegNo, setBirthRegNo] = useState("");
  const [presentAddress, setPresentAddress] = useState("");
  const [permanentAddress, setPermanentAddress] = useState("");
  const [emergencyName, setEmergencyName] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");

  const [quotaCategory, setQuotaCategory] = useState("none");
  const [isOrphan, setIsOrphan] = useState(false);
  const [hasDisability, setHasDisability] = useState(false);
  const [disabilityDetails, setDisabilityDetails] = useState("");
  const [hasStipend, setHasStipend] = useState(false);

  const [formError, setFormError] = useState<string | null>(null);

  // Sync state whenever student changes or modal opens
  useEffect(() => {
    if (student && open) {
      setNameEn(student.name_en || "");
      setNameBn(student.name_bn || "");
      setDob((student as StudentDetail).dob || "");
      setGender(student.gender || "male");
      setBloodGroup((student.blood_group as string) || "");
      setReligion((student.religion as string) || "islam");
      setStatus((student.status as string) || "active");
      setAdmissionDate((student as StudentDetail).admission_date || "");

      setPhone(student.phone || "");
      setBirthRegNo((student as StudentDetail).birth_reg_no || "");
      setPresentAddress((student as StudentDetail).present_address || "");
      setPermanentAddress((student as StudentDetail).permanent_address || "");
      setEmergencyName((student as StudentDetail).emergency_contact_name || "");
      setEmergencyPhone((student as StudentDetail).emergency_contact_phone || "");

      setQuotaCategory((student as StudentDetail).quota_category || "none");
      setIsOrphan(Boolean((student as StudentDetail).is_orphan));
      setHasDisability(Boolean((student as StudentDetail).has_disability));
      setDisabilityDetails((student as StudentDetail).disability_details || "");
      setHasStipend(Boolean((student as StudentDetail).has_stipend));
      setFormError(null);
      setActiveTab("general");
    }
  }, [student, open]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!student) throw new Error("No student selected");
      if (!nameEn.trim()) throw new Error("Student English name is required.");
      if (!nameBn.trim()) throw new Error("Student Bengali name is required.");
      if (!dob) throw new Error("Date of birth is required.");

      if (birthRegNo.trim() && (birthRegNo.trim().length !== 17 || !/^\d+$/.test(birthRegNo.trim()))) {
        throw new Error("Bangladeshi Birth Registration Number must be exactly 17 digits.");
      }

      return studentsApi.updateStudent(student.id, {
        name_en: nameEn.trim(),
        name_bn: nameBn.trim(),
        dob,
        gender: gender as never,
        blood_group: (bloodGroup || undefined) as never,
        religion: (religion || undefined) as never,
        status: status as never,
        admission_date: admissionDate || undefined,
        phone: phone.trim() || undefined,
        birth_reg_no: birthRegNo.trim() || undefined,
        present_address: presentAddress.trim(),
        permanent_address: permanentAddress.trim(),
        emergency_contact_name: emergencyName.trim(),
        emergency_contact_phone: emergencyPhone.trim(),
        quota_category: quotaCategory || undefined,
        is_orphan: isOrphan,
        has_disability: hasDisability,
        disability_details: hasDisability ? disabilityDetails.trim() : "",
        has_stipend: hasStipend,
      });
    },
    onSuccess: () => {
      toast.success(t("students.updateSuccess", "Student profile updated successfully."));
      if (student) {
        void queryClient.invalidateQueries({ queryKey: ["student", student.id] });
      }
      void queryClient.invalidateQueries({ queryKey: ["students"] });
      onSuccess?.();
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      const msg = (err as Error).message || "Failed to update student profile.";
      setFormError(msg);
      toast.error(msg);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
            <span>{t("students.editProfile", "Edit Student Profile")}</span>
          </DialogTitle>
          <DialogDescription>
            {t("students.editProfileSubtitle", "Update academic and demographic details for")} {" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {student?.name_en} ({student?.student_id})
            </span>
          </DialogDescription>
        </DialogHeader>

        {formError && (
          <div className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/50">
            {formError}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("general")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "general"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("students.tabGeneral", "General & Academic")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("contact")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "contact"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("students.tabContact", "Contact & Identification")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("special")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "special"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("students.tabSpecial", "Quota & Special Status")}
          </button>
        </div>

        {/* Tab Contents */}
        {activeTab === "general" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel required>{t("students.nameEn", "Full Name (English)")}</FormLabel>
                <Input
                  value={nameEn}
                  onChange={(e) => setNameEn(e.target.value)}
                  placeholder="e.g. Tanvir Ahmed"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel required>{t("students.nameBn", "Full Name (Bangla)")}</FormLabel>
                <Input
                  value={nameBn}
                  onChange={(e) => setNameBn(e.target.value)}
                  placeholder="যেমন: তানভীর আহমেদ"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel required>{t("students.dob", "Date of Birth")}</FormLabel>
                <Input
                  type="date"
                  value={dob}
                  onChange={(e) => setDob(e.target.value)}
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel required>{t("students.gender", "Gender")}</FormLabel>
                <Select value={gender} onValueChange={setGender}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="male">{t("common.male", "Male")}</SelectItem>
                    <SelectItem value="female">{t("common.female", "Female")}</SelectItem>
                    <SelectItem value="other">{t("common.other", "Other")}</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("students.bloodGroup", "Blood Group")}</FormLabel>
                <Select value={bloodGroup} onValueChange={setBloodGroup}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select blood group" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="A+">A+</SelectItem>
                    <SelectItem value="A-">A-</SelectItem>
                    <SelectItem value="B+">B+</SelectItem>
                    <SelectItem value="B-">B-</SelectItem>
                    <SelectItem value="O+">O+</SelectItem>
                    <SelectItem value="O-">O-</SelectItem>
                    <SelectItem value="AB+">AB+</SelectItem>
                    <SelectItem value="AB-">AB-</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("students.religion", "Religion")}</FormLabel>
                <Select value={religion} onValueChange={setReligion}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select religion" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="islam">Islam</SelectItem>
                    <SelectItem value="hinduism">Hinduism</SelectItem>
                    <SelectItem value="buddhism">Buddhism</SelectItem>
                    <SelectItem value="christianity">Christianity</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("students.status", "Enrollment Status")}</FormLabel>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                    <SelectItem value="transferred">Transferred</SelectItem>
                    <SelectItem value="graduated">Graduated</SelectItem>
                    <SelectItem value="suspended">Suspended</SelectItem>
                    <SelectItem value="dropped_out">Dropped Out</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("students.admissionDate", "Admission Date")}</FormLabel>
                <Input
                  type="date"
                  value={admissionDate}
                  onChange={(e) => setAdmissionDate(e.target.value)}
                  className="text-xs"
                />
              </FormField>
            </div>
          </div>
        )}

        {activeTab === "contact" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel>{t("students.phone", "Student Phone (for Mobile App)")}</FormLabel>
                <Input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="01XXXXXXXXX"
                  className="text-xs font-mono"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("students.birthRegNo", "Birth Registration No (17 digits)")}</FormLabel>
                <Input
                  value={birthRegNo}
                  onChange={(e) => setBirthRegNo(e.target.value)}
                  placeholder="17-digit birth cert number"
                  maxLength={17}
                  className="text-xs font-mono"
                />
              </FormField>

              <FormField className="sm:col-span-2">
                <FormLabel>{t("students.presentAddress", "Present Address")}</FormLabel>
                <Input
                  value={presentAddress}
                  onChange={(e) => setPresentAddress(e.target.value)}
                  placeholder="Holding, Road, Ward, Post Office, Upazila, District"
                  className="text-xs"
                />
              </FormField>

              <FormField className="sm:col-span-2">
                <FormLabel>{t("students.permanentAddress", "Permanent Address")}</FormLabel>
                <Input
                  value={permanentAddress}
                  onChange={(e) => setPermanentAddress(e.target.value)}
                  placeholder="Village/Road, Post Office, Upazila, District"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("students.emergencyName", "Emergency Contact Person")}</FormLabel>
                <Input
                  value={emergencyName}
                  onChange={(e) => setEmergencyName(e.target.value)}
                  placeholder="Guardian or Relative Name"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("students.emergencyPhone", "Emergency Contact Phone")}</FormLabel>
                <Input
                  value={emergencyPhone}
                  onChange={(e) => setEmergencyPhone(e.target.value)}
                  placeholder="01XXXXXXXXX"
                  className="text-xs font-mono"
                />
              </FormField>
            </div>
          </div>
        )}

        {activeTab === "special" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel>{t("students.quotaCategory", "Quota Category")}</FormLabel>
                <Select value={quotaCategory} onValueChange={setQuotaCategory}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select quota" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">General / None</SelectItem>
                    <SelectItem value="freedom_fighter">Freedom Fighter (মুক্তিযোদ্ধা)</SelectItem>
                    <SelectItem value="tribal">Tribal / Ethnic (ক্ষুদ্র নৃগোষ্ঠী)</SelectItem>
                    <SelectItem value="disability">Disability (প্রতিবন্ধী)</SelectItem>
                    <SelectItem value="special">Special Quota</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <div className="flex flex-col justify-end space-y-2 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={hasStipend}
                    onChange={(e) => setHasStipend(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-800"
                  />
                  <span>{t("students.hasStipend", "Receives Govt / NGO Stipend (উপবৃত্তিপ্রাপ্ত)")}</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={isOrphan}
                    onChange={(e) => setIsOrphan(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-800"
                  />
                  <span>{t("students.isOrphan", "Orphan Child (এতিম শিক্ষার্থী)")}</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={hasDisability}
                    onChange={(e) => setHasDisability(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-800"
                  />
                  <span>{t("students.hasDisability", "Special Needs / Disability")}</span>
                </label>
              </div>

              {hasDisability && (
                <FormField className="sm:col-span-2">
                  <FormLabel>{t("students.disabilityDetails", "Disability Description & Accommodations")}</FormLabel>
                  <Input
                    value={disabilityDetails}
                    onChange={(e) => setDisabilityDetails(e.target.value)}
                    placeholder="e.g. Visual impairment, wheel chair accessible desk required"
                    className="text-xs"
                  />
                </FormField>
              )}
            </div>
          </div>
        )}

        <DialogFooter className="mt-4 gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="text-xs"
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={updateMutation.isPending}
            onClick={() => updateMutation.mutate()}
            className="text-xs bg-emerald-800 hover:bg-emerald-900 text-white font-semibold"
          >
            {updateMutation.isPending ? t("common.saving", "Saving...") : t("common.saveChanges", "Save Changes")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
