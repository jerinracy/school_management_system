import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Briefcase } from "lucide-react";

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
import { staffApi, type StaffDetail, type StaffListItem } from "@/features/staff/api/staffApi";

interface EditStaffDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  staff: StaffDetail | StaffListItem | null;
  onSuccess?: () => void;
}

export function EditStaffDialog({
  open,
  onOpenChange,
  staff,
  onSuccess,
}: EditStaffDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"basic" | "employment" | "contact" | "mpo">("basic");

  // Form State
  const [fullNameEn, setFullNameEn] = useState("");
  const [fullNameBn, setFullNameBn] = useState("");
  const [gender, setGender] = useState("male");
  const [dob, setDob] = useState("");
  const [bloodGroup, setBloodGroup] = useState("");

  const [staffType, setStaffType] = useState("teacher");
  const [departmentId, setDepartmentId] = useState("");
  const [designationId, setDesignationId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [status, setStatus] = useState("active");
  const [joiningDate, setJoiningDate] = useState("");
  const [confirmationDate, setConfirmationDate] = useState("");

  const [phone, setPhone] = useState("");
  const [altPhone, setAltPhone] = useState("");
  const [email, setEmail] = useState("");
  const [presentAddress, setPresentAddress] = useState("");
  const [permanentAddress, setPermanentAddress] = useState("");

  const [nid, setNid] = useState("");
  const [isMpo, setIsMpo] = useState(false);
  const [mpoIndexNumber, setMpoIndexNumber] = useState("");
  const [tinNumber, setTinNumber] = useState("");

  const [emergencyName, setEmergencyName] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");
  const [emergencyRelation, setEmergencyRelation] = useState("Spouse");

  const [formError, setFormError] = useState<string | null>(null);

  // Queries for options
  const { data: departmentsData } = useQuery({
    queryKey: ["staff-departments"],
    queryFn: () => staffApi.getDepartments(),
    enabled: open,
  });

  const { data: designationsData } = useQuery({
    queryKey: ["staff-designations"],
    queryFn: () => staffApi.getDesignations(),
    enabled: open,
  });

  const { data: branchesData } = useQuery({
    queryKey: ["institutions-branches"],
    queryFn: () => staffApi.getBranches(),
    enabled: open,
  });

  const departments = departmentsData?.results ?? [];
  const designations = designationsData?.results ?? [];
  const branches = (branchesData?.results as Array<{ id: string; name: string; code: string }>) ?? [];

  // Populate state on open or staff change
  useEffect(() => {
    if (staff && open) {
      setFullNameEn(staff.full_name_en || "");
      setFullNameBn(staff.full_name_bn || "");
      setGender(((staff as StaffDetail).gender as string) || "male");
      setDob((staff as StaffDetail).dob || "");
      setBloodGroup(((staff as StaffDetail).blood_group as string) || "");

      setStaffType((staff as StaffDetail).staff_type || "teacher");
      setDepartmentId((staff as StaffDetail).department || "");
      setDesignationId((staff as StaffDetail).designation || "");
      setBranchId((staff as StaffDetail).branch || "");
      setStatus((staff.status as string) || "active");
      setJoiningDate((staff as StaffDetail).joining_date || "");
      setConfirmationDate((staff as StaffDetail).confirmation_date || "");

      setPhone(staff.phone || "");
      setAltPhone((staff as StaffDetail).alt_phone || "");
      setEmail((staff as StaffDetail).email || "");
      setPresentAddress((staff as StaffDetail).present_address || "");
      setPermanentAddress((staff as StaffDetail).permanent_address || "");

      setNid((staff as StaffDetail).nid || "");
      setIsMpo(Boolean(staff.is_mpo));
      setMpoIndexNumber((staff as StaffDetail).mpo_index_number || "");
      setTinNumber((staff as StaffDetail).tin_number || "");

      setEmergencyName((staff as StaffDetail).emergency_contact_name || "");
      setEmergencyPhone((staff as StaffDetail).emergency_contact_phone || "");
      setEmergencyRelation((staff as StaffDetail).emergency_contact_relation || "Spouse");

      setFormError(null);
      setActiveTab("basic");
    }
  }, [staff, open]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!staff) throw new Error("No staff selected");
      if (!fullNameEn.trim()) throw new Error("Full Name (English) is required.");
      if (!phone.trim()) throw new Error("Phone number is required.");

      return staffApi.updateStaff(staff.id, {
        full_name_en: fullNameEn.trim(),
        full_name_bn: fullNameBn.trim(),
        gender: gender as never,
        dob: dob || undefined,
        blood_group: bloodGroup || undefined,
        staff_type: staffType as never,
        department: departmentId || undefined,
        designation: designationId || undefined,
        branch: branchId || undefined,
        status: status as never,
        joining_date: joiningDate || undefined,
        confirmation_date: confirmationDate || undefined,
        phone: phone.trim(),
        alt_phone: altPhone.trim() || undefined,
        email: email.trim() || undefined,
        present_address: presentAddress.trim(),
        permanent_address: permanentAddress.trim(),
        nid: nid.trim() || undefined,
        is_mpo: isMpo,
        mpo_index_number: isMpo ? mpoIndexNumber.trim() : "",
        tin_number: tinNumber.trim() || undefined,
        emergency_contact_name: emergencyName.trim(),
        emergency_contact_phone: emergencyPhone.trim(),
        emergency_contact_relation: emergencyRelation.trim(),
      });
    },
    onSuccess: () => {
      toast.success(t("staff.updateSuccess", "Employee profile updated successfully."));
      if (staff) {
        void queryClient.invalidateQueries({ queryKey: ["staff", staff.id] });
      }
      void queryClient.invalidateQueries({ queryKey: ["staff"] });
      onSuccess?.();
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      const msg = (err as Error).message || "Failed to update employee profile.";
      setFormError(msg);
      toast.error(msg);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
            <span>
              {staffType === "teacher"
                ? t("staff.editTeacherProfile", "Edit Teacher Profile")
                : t("staff.editStaffProfile", "Edit Employee Profile")}
            </span>
          </DialogTitle>
          <DialogDescription>
            {t("staff.editSubtitle", "Update employment and identity details for")} {" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {staff?.full_name_en} ({staff?.employee_id})
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
            onClick={() => setActiveTab("basic")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "basic"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("staff.tabBasic", "Basic Identity")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("employment")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "employment"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("staff.tabEmployment", "Role & Department")}
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
            {t("staff.tabContact", "Contact & Address")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("mpo")}
            className={`px-3 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "mpo"
                ? "border-emerald-800 text-emerald-800 dark:border-emerald-400 dark:text-emerald-400 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t("staff.tabMpo", "MPO, NID & Tax")}
          </button>
        </div>

        {/* Tab 1: Basic Identity */}
        {activeTab === "basic" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel required>{t("staff.fullNameEn", "Full Name (English)")}</FormLabel>
                <Input
                  value={fullNameEn}
                  onChange={(e) => setFullNameEn(e.target.value)}
                  placeholder="e.g. Dr. Mohammad Ali"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.fullNameBn", "Full Name (Bangla)")}</FormLabel>
                <Input
                  value={fullNameBn}
                  onChange={(e) => setFullNameBn(e.target.value)}
                  placeholder="যেমন: ড. মোহাম্মদ আলী"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel required>{t("staff.gender", "Gender")}</FormLabel>
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
                <FormLabel>{t("staff.dob", "Date of Birth")}</FormLabel>
                <Input
                  type="date"
                  value={dob}
                  onChange={(e) => setDob(e.target.value)}
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.bloodGroup", "Blood Group")}</FormLabel>
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
            </div>
          </div>
        )}

        {/* Tab 2: Role & Employment */}
        {activeTab === "employment" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel required>{t("staff.staffType", "Staff Classification")}</FormLabel>
                <Select value={staffType} onValueChange={setStaffType}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select staff type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="teacher">{t("staff.teacher", "Teacher (শিক্ষক)")}</SelectItem>
                    <SelectItem value="admin">{t("staff.adminStaff", "Administrative Staff")}</SelectItem>
                    <SelectItem value="support">{t("staff.supportStaff", "Support Staff")}</SelectItem>
                    <SelectItem value="driver">{t("staff.driver", "Driver (চালক)")}</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("staff.status", "Employment Status")}</FormLabel>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active (সক্রিয়)</SelectItem>
                    <SelectItem value="on_leave">On Leave (ছুটিতে)</SelectItem>
                    <SelectItem value="suspended">Suspended</SelectItem>
                    <SelectItem value="resigned">Resigned</SelectItem>
                    <SelectItem value="retired">Retired</SelectItem>
                    <SelectItem value="terminated">Terminated</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("staff.department", "Department")}</FormLabel>
                <Select value={departmentId} onValueChange={setDepartmentId}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map((d) => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField>
                <FormLabel>{t("staff.designation", "Designation / Title")}</FormLabel>
                <Select value={designationId} onValueChange={setDesignationId}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Select designation" />
                  </SelectTrigger>
                  <SelectContent>
                    {designations.map((d) => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.title} {d.title_bn ? `(${d.title_bn})` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              {branches.length > 0 && (
                <FormField>
                  <FormLabel>{t("staff.branch", "Assigned Campus / Branch")}</FormLabel>
                  <Select value={branchId} onValueChange={setBranchId}>
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="Select campus branch" />
                    </SelectTrigger>
                    <SelectContent>
                      {branches.map((b) => (
                        <SelectItem key={b.id} value={b.id}>
                          {b.name} ({b.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              )}

              <FormField>
                <FormLabel>{t("staff.joiningDate", "Joining Date")}</FormLabel>
                <Input
                  type="date"
                  value={joiningDate}
                  onChange={(e) => setJoiningDate(e.target.value)}
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.confirmationDate", "Confirmation Date")}</FormLabel>
                <Input
                  type="date"
                  value={confirmationDate}
                  onChange={(e) => setConfirmationDate(e.target.value)}
                  className="text-xs"
                />
              </FormField>
            </div>
          </div>
        )}

        {/* Tab 3: Contact & Address */}
        {activeTab === "contact" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel required>{t("staff.phone", "Primary Phone (Mobile App Login)")}</FormLabel>
                <Input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="01XXXXXXXXX"
                  className="text-xs font-mono"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.altPhone", "Alternate Phone")}</FormLabel>
                <Input
                  value={altPhone}
                  onChange={(e) => setAltPhone(e.target.value)}
                  placeholder="01XXXXXXXXX"
                  className="text-xs font-mono"
                />
              </FormField>

              <FormField className="sm:col-span-2">
                <FormLabel>{t("staff.email", "Email Address")}</FormLabel>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@school.edu.bd"
                  className="text-xs"
                />
              </FormField>

              <FormField className="sm:col-span-2">
                <FormLabel>{t("staff.presentAddress", "Present Address")}</FormLabel>
                <Input
                  value={presentAddress}
                  onChange={(e) => setPresentAddress(e.target.value)}
                  placeholder="Holding, Road, Ward, Post Office, Upazila, District"
                  className="text-xs"
                />
              </FormField>

              <FormField className="sm:col-span-2">
                <FormLabel>{t("staff.permanentAddress", "Permanent Address")}</FormLabel>
                <Input
                  value={permanentAddress}
                  onChange={(e) => setPermanentAddress(e.target.value)}
                  placeholder="Village/Road, Post Office, Upazila, District"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.emergencyName", "Emergency Contact Person")}</FormLabel>
                <Input
                  value={emergencyName}
                  onChange={(e) => setEmergencyName(e.target.value)}
                  placeholder="e.g. Spouse / Sibling Name"
                  className="text-xs"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.emergencyPhone", "Emergency Contact Phone")}</FormLabel>
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

        {/* Tab 4: MPO, NID & Tax */}
        {activeTab === "mpo" && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField>
                <FormLabel>{t("staff.nid", "National ID (NID)")}</FormLabel>
                <Input
                  value={nid}
                  onChange={(e) => setNid(e.target.value)}
                  placeholder="10, 13, or 17 digit NID"
                  className="text-xs font-mono"
                />
              </FormField>

              <FormField>
                <FormLabel>{t("staff.tinNumber", "TIN Number (12 digits)")}</FormLabel>
                <Input
                  value={tinNumber}
                  onChange={(e) => setTinNumber(e.target.value)}
                  placeholder="e.g. 123456789012"
                  className="text-xs font-mono"
                />
              </FormField>

              <div className="sm:col-span-2 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={isMpo}
                    onChange={(e) => setIsMpo(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-800"
                  />
                  <span>{t("staff.isMpo", "MPO Enlisted Personnel (এমপিওভুক্ত কর্মী)")}</span>
                </label>
              </div>

              {isMpo && (
                <FormField className="sm:col-span-2">
                  <FormLabel>{t("staff.mpoIndex", "MPO Index Number")}</FormLabel>
                  <Input
                    value={mpoIndexNumber}
                    onChange={(e) => setMpoIndexNumber(e.target.value)}
                    placeholder="e.g. 1045678"
                    className="text-xs font-mono"
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
