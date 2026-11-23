import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface AcademicLogoProps {
  logoUrl?: string | null;
  name?: string;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeClasses = {
  sm: "h-9 w-9 rounded-lg text-sm",
  md: "h-12 w-12 rounded-xl text-base",
  lg: "h-16 w-16 rounded-2xl text-xl",
  xl: "h-20 w-20 rounded-2xl text-2xl",
};

export function AcademicLogo({
  logoUrl,
  name = "School Management System",
  className,
  size = "md",
}: AcademicLogoProps) {
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    setImageError(false);
  }, [logoUrl]);

  // If a valid custom logo is uploaded from the Admin panel and hasn't errored
  if (logoUrl && !imageError) {
    return (
      <div
        className={cn(
          "relative flex shrink-0 items-center justify-center overflow-hidden border border-border/80 bg-white p-2 shadow-2xs transition-all",
          sizeClasses[size],
          className,
        )}
      >
        <img
          src={logoUrl}
          alt={name}
          onError={() => setImageError(true)}
          className="h-full w-full object-contain"
        />
      </div>
    );
  }

  // High-craft, elegant Academic Emblem / Crest Demo Logo SVG
  return (
    <div
      role="img"
      aria-label={name}
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden border border-border/80 bg-canvas text-primary transition-colors",
        sizeClasses[size],
        className,
      )}
    >
      <svg
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-4/5 w-4/5 text-primary"
        aria-hidden="true"
      >
        {/* Outer shield frame */}
        <path
          d="M32 4L12 12V28C12 41.5 20.6 53.8 32 60C43.4 53.8 52 41.5 52 28V12L32 4Z"
          fill="currentColor"
          fillOpacity="0.12"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Inner decorative border */}
        <path
          d="M32 9L16 15.5V28C16 39.5 22.8 49.8 32 55C41.2 49.8 48 39.5 48 28V15.5L32 9Z"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeOpacity="0.35"
          strokeDasharray="2 2"
        />

        {/* Graduation cap */}
        <path
          d="M32 17L18 24L32 31L46 24L32 17Z"
          fill="currentColor"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M24 27V34C24 36.8 27.6 39 32 39C36.4 39 40 36.8 40 34V27"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        {/* Tassel */}
        <path
          d="M44 25.5V33.5"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <circle cx="44" cy="34" r="1.2" fill="currentColor" />

        {/* Open book of knowledge */}
        <path
          d="M22 46C26 44 30 45 32 47C34 45 38 44 42 46V51C38 49 34 50 32 52C30 50 26 49 22 51V46Z"
          fill="currentColor"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
