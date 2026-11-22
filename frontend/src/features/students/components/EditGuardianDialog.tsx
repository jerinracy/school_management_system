import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Users } from "lucide-react";

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
import { studentsApi, type GuardianItem } from "@/features/students/api/studentsApi";

interface EditGuardianDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  guardian: GuardianItem | null;
  onSuccess?: () => void;
}

export function EditGuardianDialog({
  open,
  onOpenChange,
  guardian,
  onSuccess,
}: EditGuardianDialogProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [nameEn, setNameEn] = useState("");
  const [nameBn, setNameBn] = useState("");
  const [phone, setPhone] = useState("");
  const [altPhone, setAltPhone] = useState("");
  const [email, setEmail] = useState("");
  const [nid, setNid] = useState("");
  const [occupation, setOccupation] = useState("");
  const [annualIncome, setAnnualIncome] = useState("");
  const [relationDefault, setRelationDefault] = useState("father");
  const [presentAddress, setPresentAddress] = useState("");
  const [permanentAddress, setPermanentAddress] = useState("");
  const [isEmergencyContact, setIsEmergencyContact] = useState(true);

  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (guardian && open) {
      setNameEn(guardian.name_en || "");
      setNameBn(guardian.name_bn || "");
      setPhone(guardian.phone || "");
      setAltPhone(guardian.alt_phone || "");
      setEmail(guardian.email || "");
      setNid(guardian.nid || "");
      setOccupation(guardian.occupation || "");
      setAnnualIncome(guardian.annual_income ? String(guardian.annual_income) : "");
      setRelationDefault((guardian.relation_default as string) || "father");
      setPresentAddress(guardian.present_address || "");
      setPermanentAddress(guardian.permanent_address || "");
      setIsEmergencyContact(Boolean(guardian.is_emergency_contact));
      setFormError(null);
    }
  }, [guardian, open]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!guardian) throw new Error("No guardian selected");
      if (!nameEn.trim()) throw new Error("Guardian English name is required.");
      if (!phone.trim()) throw new Error("Guardian phone number is required.");

      return studentsApi.updateGuardian(guardian.id, {
        name_en: nameEn.trim(),
        name_bn: nameBn.trim(),
        phone: phone.trim(),
        alt_phone: altPhone.trim() || undefined,
        email: email.trim() || undefined,
        nid: nid.trim() || undefined,
        occupation: occupation.trim() || undefined,
        annual_income: annualIncome ? String(annualIncome).trim() : undefined,
        relation_default: relationDefault as never,
        present_address: presentAddress.trim(),
        permanent_address: permanentAddress.trim(),
        is_emergency_contact: isEmergencyContact,
      });
    },
    onSuccess: () => {
      toast.success(t("guardians.updateSuccess", "Guardian details updated successfully."));
      void queryClient.invalidateQueries({ queryKey: ["guardians"] });
      onSuccess?.();
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      const msg = (err as Error).message || "Failed to update guardian details.";
      setFormError(msg);
      toast.error(msg);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-emerald-800 dark:text-emerald-400" />
            <span>{t("guardians.editTitle", "Edit Guardian Profile")}</span>
          </DialogTitle>
          <DialogDescription>
            {t("guardians.editSubtitle", "Update contact and identity details for")} {" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {guardian?.name_en}
            </span>
          </DialogDescription>
        </DialogHeader>

        {formError && (
          <div className="rounded-lg bg-rose-50 dark:bg-rose-950/50 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/50">
            {formError}
          </div>
        )}

        <div className="space-y-4 pt-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <FormField>
              <FormLabel required>{t("guardians.nameEn", "Full Name (English)")}</FormLabel>
              <Input
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                placeholder="e.g. Mohammad Harun"
                className="text-xs"
              />
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.nameBn", "Full Name (Bangla)")}</FormLabel>
              <Input
                value={nameBn}
                onChange={(e) => setNameBn(e.target.value)}
                placeholder="যেমন: মোহাম্মদ হারুন"
                className="text-xs"
              />
            </FormField>

            <FormField>
              <FormLabel required>{t("guardians.phone", "Primary Phone (Mobile App Login)")}</FormLabel>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="01XXXXXXXXX"
                className="text-xs font-mono"
              />
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.altPhone", "Alternate Phone")}</FormLabel>
              <Input
                value={altPhone}
                onChange={(e) => setAltPhone(e.target.value)}
                placeholder="01XXXXXXXXX"
                className="text-xs font-mono"
              />
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.relationDefault", "Default Relation")}</FormLabel>
              <Select value={relationDefault} onValueChange={setRelationDefault}>
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Select relation" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="father">Father (পিতা)</SelectItem>
                  <SelectItem value="mother">Mother (মাতা)</SelectItem>
                  <SelectItem value="other">Other Legal Guardian (আইনগত অভিভাবক)</SelectItem>
                </SelectContent>
              </Select>
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.nid", "National ID (NID)")}</FormLabel>
              <Input
                value={nid}
                onChange={(e) => setNid(e.target.value)}
                placeholder="10, 13, or 17 digits"
                className="text-xs font-mono"
              />
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.occupation", "Occupation")}</FormLabel>
              <Input
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                placeholder="e.g. Teacher, Business, Engineer"
                className="text-xs"
              />
            </FormField>

            <FormField>
              <FormLabel>{t("guardians.annualIncome", "Annual Income (BDT ৳)")}</FormLabel>
              <Input
                type="number"
                value={annualIncome}
                onChange={(e) => setAnnualIncome(e.target.value)}
                placeholder="e.g. 500000"
                className="text-xs"
              />
            </FormField>

            <FormField className="sm:col-span-2">
              <FormLabel>{t("guardians.email", "Email Address")}</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="guardian@example.com"
                className="text-xs"
              />
            </FormField>

            <FormField className="sm:col-span-2">
              <FormLabel>{t("guardians.presentAddress", "Present Address")}</FormLabel>
              <Input
                value={presentAddress}
                onChange={(e) => setPresentAddress(e.target.value)}
                placeholder="Holding, Road, Ward, Post Office, Upazila, District"
                className="text-xs"
              />
            </FormField>

            <FormField className="sm:col-span-2">
              <FormLabel>{t("guardians.permanentAddress", "Permanent Address")}</FormLabel>
              <Input
                value={permanentAddress}
                onChange={(e) => setPermanentAddress(e.target.value)}
                placeholder="Village/Road, Post Office, Upazila, District"
                className="text-xs"
              />
            </FormField>

            <div className="sm:col-span-2 pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={isEmergencyContact}
                  onChange={(e) => setIsEmergencyContact(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-emerald-800 focus:ring-emerald-800"
                />
                <span>{t("guardians.isEmergencyContact", "Designated Emergency Contact Person")}</span>
              </label>
            </div>
          </div>
        </div>

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
