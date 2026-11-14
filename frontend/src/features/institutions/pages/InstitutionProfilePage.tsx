import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { Building2, Save, Upload } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/composite/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { institutionApi, type InstitutionProfile } from "@/features/institutions/api/institutionApi";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";

export function InstitutionProfilePage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<InstitutionProfile | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const fetchBranding = useBrandingStore((s) => s.fetchBranding);

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm();

  useEffect(() => {
    async function load() {
      try {
        const data = await institutionApi.getProfile();
        setProfile(data);
        reset(data);
      } catch {
        toast.error(t("institution.loadProfileError", "Failed to load institution profile."));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [reset, t]);

  const onSubmit = async (data: Record<string, unknown>) => {
    try {
      const formData = new FormData();
      Object.entries(data).forEach(([key, val]) => {
        if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
          formData.append(key, String(val));
        }
      });
      if (logoFile) {
        formData.append("logo", logoFile);
      }

      const updated = await institutionApi.updateProfile(formData);
      setProfile(updated);
      void fetchBranding(true);
      toast.success(t("institution.profileSaved", "Institution details updated."));
    } catch {
      toast.error(t("institution.profileSaveError", "Failed to save profile changes."));
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-xs text-ink-muted">{t("common.loading", "Loading...")}</div>;
  }

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title={t("institution.profileTitle", "Institution Profile & Identity")}
        subtitle={t("institution.profileSubtitle", "Configure EIIN, school branding, official seal, and institutional metadata.")}
      />

      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Building2 className="h-4 w-4 text-primary" />
                {t("institution.generalInfo", "Basic Information")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField>
                  <FormLabel htmlFor="name_en" required>{t("institution.nameEn", "Name (English)")}</FormLabel>
                  <Input id="name_en" {...register("name_en")} />
                </FormField>
                <FormField>
                  <FormLabel htmlFor="name_bn" required>{t("institution.nameBn", "Name (Bangla)")}</FormLabel>
                  <Input id="name_bn" {...register("name_bn")} />
                </FormField>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <FormField>
                  <FormLabel htmlFor="eiin" required>{t("institution.eiin", "EIIN Number")}</FormLabel>
                  <Input id="eiin" {...register("eiin")} />
                </FormField>
                <FormField>
                  <FormLabel htmlFor="code" required>{t("institution.code", "Institution Code")}</FormLabel>
                  <Input id="code" {...register("code")} />
                </FormField>
                <FormField>
                  <FormLabel htmlFor="phone">{t("institution.phone", "Contact Phone")}</FormLabel>
                  <Input id="phone" {...register("phone")} />
                </FormField>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField>
                  <FormLabel htmlFor="email">{t("institution.email", "Contact Email")}</FormLabel>
                  <Input id="email" type="email" {...register("email")} />
                </FormField>
                <FormField>
                  <FormLabel htmlFor="website">{t("institution.website", "Official Website")}</FormLabel>
                  <Input id="website" {...register("website")} />
                </FormField>
              </div>

              <FormField>
                <FormLabel htmlFor="address">{t("institution.address", "Campus Address")}</FormLabel>
                <Input id="address" {...register("address")} />
              </FormField>

              <div className="pt-2">
                <Button type="submit" disabled={isSubmitting}>
                  <Save className="h-3.5 w-3.5 mr-1" />
                  {isSubmitting ? t("common.loading", "Saving...") : t("common.saveChanges", "Save Changes")}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Upload className="h-4 w-4 text-primary" />
                {t("institution.branding", "School Logo & Seal")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-6 text-center">
                {profile?.logo ? (
                  <img src={profile.logo} alt="School Logo" className="h-20 w-20 object-contain mb-2 rounded" />
                ) : (
                  <Building2 className="h-16 w-16 text-ink-subtle mb-2" />
                )}
                <label className="cursor-pointer text-xs font-semibold text-primary hover:underline">
                  <span>{t("institution.uploadLogo", "Upload Official Logo")}</span>
                  <input
                    type="file"
                    className="sr-only"
                    accept="image/png,image/jpeg"
                    onChange={(e) => {
                      if (e.target.files?.[0]) setLogoFile(e.target.files[0]);
                    }}
                  />
                </label>
                <p className="mt-1 text-[10px] text-ink-muted">PNG or JPG up to 2MB</p>
                {logoFile && <p className="mt-1 text-xs text-emerald-600 font-medium">{logoFile.name}</p>}
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </div>
  );
}
