import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { Building2, CheckCircle2, Image as ImageIcon, RotateCcw, Save, Trash2, Upload } from "lucide-react";
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

  // Logo state
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);

  // Background state
  const [bgFile, setBgFile] = useState<File | null>(null);
  const [bgPreview, setBgPreview] = useState<string | null>(null);
  const [isUploadingBg, setIsUploadingBg] = useState(false);
  const [removeBg, setRemoveBg] = useState(false);

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

  // Dedicated Logo confirmation handler
  const handleConfirmLogo = async () => {
    if (!logoFile) return;
    setIsUploadingLogo(true);
    try {
      const formData = new FormData();
      formData.append("logo", logoFile);
      const updated = await institutionApi.updateProfile(formData);
      setProfile(updated);
      setLogoFile(null);
      setLogoPreview(null);
      await fetchBranding(true);
      toast.success(t("institution.logoUpdated", "School logo updated successfully."));
    } catch {
      toast.error(t("institution.logoUpdateError", "Failed to upload school logo."));
    } finally {
      setIsUploadingLogo(false);
    }
  };

  // Dedicated Login Background confirmation handler
  const handleConfirmBg = async () => {
    if (!bgFile && !removeBg) return;
    setIsUploadingBg(true);
    try {
      const formData = new FormData();
      if (bgFile) {
        formData.append("login_background", bgFile);
      } else if (removeBg) {
        formData.append("login_background", "");
      }
      const updated = await institutionApi.updateProfile(formData);
      setProfile(updated);
      setBgFile(null);
      setBgPreview(null);
      setRemoveBg(false);
      await fetchBranding(true);
      toast.success(
        removeBg
          ? t("institution.bgRemoved", "Login background removed.")
          : t("institution.bgUpdated", "Login background image updated successfully.")
      );
    } catch {
      toast.error(t("institution.bgUpdateError", "Failed to update login background image."));
    } finally {
      setIsUploadingBg(false);
    }
  };

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
      if (bgFile) {
        formData.append("login_background", bgFile);
      } else if (removeBg) {
        formData.append("login_background", "");
      }

      const updated = await institutionApi.updateProfile(formData);
      setProfile(updated);
      setLogoFile(null);
      setLogoPreview(null);
      setBgFile(null);
      setBgPreview(null);
      setRemoveBg(false);
      await fetchBranding(true);
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

          <div className="space-y-6 lg:col-span-1">
            {/* School Logo Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Upload className="h-4 w-4 text-primary" />
                  {t("institution.branding", "School Logo & Seal")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-4 text-center bg-canvas/40">
                  {logoPreview ? (
                    <div className="relative mb-2 flex flex-col items-center">
                      <img
                        src={logoPreview}
                        alt="Staged School Logo"
                        className="h-20 w-20 object-contain rounded border border-border p-1 bg-surface shadow-xs"
                      />
                      <span className="mt-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-300 px-2 py-0.5 rounded">
                        {t("institution.newLogoSelected", "New Logo Selected")}
                      </span>
                    </div>
                  ) : profile?.logo ? (
                    <img
                      src={profile.logo}
                      alt="Current School Logo"
                      className="h-20 w-20 object-contain mb-2 rounded border border-border p-1 bg-surface shadow-xs"
                    />
                  ) : (
                    <Building2 className="h-16 w-16 text-ink-subtle mb-2" />
                  )}

                  <label className="cursor-pointer text-xs font-semibold text-primary hover:underline">
                    <span>
                      {logoFile || profile?.logo
                        ? t("institution.changeLogo", "Change Logo Image")
                        : t("institution.uploadLogo", "Upload Official Logo")}
                    </span>
                    <input
                      type="file"
                      className="sr-only"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          setLogoFile(file);
                          setLogoPreview(URL.createObjectURL(file));
                        }
                      }}
                    />
                  </label>
                  <p className="mt-1 text-[10px] text-ink-muted">PNG or JPG up to 2MB</p>
                  {logoFile && <p className="mt-1 text-xs text-ink-muted truncate max-w-[200px]">{logoFile.name}</p>}

                  {/* Dedicated Confirm Button for Logo */}
                  {logoFile && (
                    <div className="mt-3 w-full flex items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void handleConfirmLogo()}
                        disabled={isUploadingLogo}
                        className="flex-1 bg-emerald-800 hover:bg-emerald-900 text-white font-semibold flex items-center justify-center gap-1.5 shadow-2xs h-8 text-xs"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>
                          {isUploadingLogo
                            ? t("common.loading", "Setting...")
                            : t("institution.confirmLogo", "Confirm & Set Logo")}
                        </span>
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setLogoFile(null);
                          setLogoPreview(null);
                        }}
                        className="h-8 px-2 text-xs text-ink-muted"
                        title={t("common.cancel", "Cancel")}
                      >
                        <RotateCcw className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Login Background Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <ImageIcon className="h-4 w-4 text-primary" />
                  {t("institution.loginBackgroundTitle", "Login Background Image")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-ink-muted leading-relaxed">
                  {t(
                    "institution.loginBackgroundHint",
                    "Upload an official school campus photograph to display on the public sign-in page.",
                  )}
                </p>

                <div className="relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-4 text-center overflow-hidden bg-canvas/40">
                  {bgPreview ? (
                    <div className="relative w-full h-32 mb-2 rounded-lg overflow-hidden border border-border shadow-xs">
                      <img src={bgPreview} alt="Background Preview" className="w-full h-full object-cover" />
                      <div className="absolute bottom-1 right-1 bg-emerald-900/80 text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
                        {t("institution.preview", "New Preview")}
                      </div>
                    </div>
                  ) : !removeBg && profile?.login_background ? (
                    <div className="relative w-full h-32 mb-2 rounded-lg overflow-hidden border border-border shadow-xs">
                      <img
                        src={profile.login_background}
                        alt="Current School Campus"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div className="py-4">
                      <ImageIcon className="h-10 w-10 text-ink-subtle mx-auto mb-1.5 opacity-60" />
                      <p className="text-xs text-ink-subtle">{t("institution.noCustomBackground", "Default campus backdrop active")}</p>
                    </div>
                  )}

                  <div className="flex items-center gap-3 mt-1">
                    <label className="cursor-pointer text-xs font-semibold text-primary hover:underline">
                      <span>
                        {bgFile || profile?.login_background
                          ? t("institution.changeBg", "Change Photo")
                          : t("institution.uploadBg", "Choose Photo")}
                      </span>
                      <input
                        type="file"
                        className="sr-only"
                        accept="image/png,image/jpeg,image/webp"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            setBgFile(file);
                            setRemoveBg(false);
                            setBgPreview(URL.createObjectURL(file));
                          }
                        }}
                      />
                    </label>

                    {(profile?.login_background || bgFile) && (
                      <button
                        type="button"
                        onClick={() => {
                          setBgFile(null);
                          setBgPreview(null);
                          setRemoveBg(true);
                        }}
                        className="inline-flex items-center gap-1 text-xs text-rose-600 hover:underline font-medium"
                      >
                        <Trash2 className="h-3 w-3" />
                        <span>{t("common.remove", "Remove")}</span>
                      </button>
                    )}
                  </div>

                  <p className="mt-1.5 text-[10px] text-ink-muted">PNG, JPG or WebP up to 5MB</p>
                  {bgFile && <p className="mt-1 text-xs text-ink-muted truncate max-w-[200px]">{bgFile.name}</p>}

                  {/* Dedicated Confirm Button for Background */}
                  {bgFile && (
                    <div className="mt-3 w-full flex items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void handleConfirmBg()}
                        disabled={isUploadingBg}
                        className="flex-1 bg-emerald-800 hover:bg-emerald-900 text-white font-semibold flex items-center justify-center gap-1.5 shadow-2xs h-8 text-xs"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>
                          {isUploadingBg
                            ? t("common.loading", "Setting...")
                            : t("institution.confirmBg", "Confirm & Set Background")}
                        </span>
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setBgFile(null);
                          setBgPreview(null);
                        }}
                        className="h-8 px-2 text-xs text-ink-muted"
                        title={t("common.cancel", "Cancel")}
                      >
                        <RotateCcw className="h-3 w-3" />
                      </Button>
                    </div>
                  )}

                  {/* Removal confirmation prompt */}
                  {removeBg && (
                    <div className="mt-3 w-full">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => void handleConfirmBg()}
                        disabled={isUploadingBg}
                        className="w-full border-rose-300 text-rose-700 hover:bg-rose-50 font-semibold flex items-center justify-center gap-1.5 h-8 text-xs"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span>
                          {isUploadingBg
                            ? t("common.loading", "Removing...")
                            : t("institution.confirmRemoveBg", "Confirm Removal")}
                        </span>
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}
