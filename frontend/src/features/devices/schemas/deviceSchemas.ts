import { z } from "zod";

export const deviceTerminalSchema = z.object({
  name: z.string().min(2, "validation.nameRequired").max(100),
  vendor: z.string().min(2, "validation.vendorRequired").max(50),
  model: z.string().max(50).optional().or(z.literal("")),
  serial_no: z.string().max(64).optional().or(z.literal("")),
  device_type: z.enum([
    "fingerprint",
    "face",
    "iris",
    "palm",
    "rfid",
    "nfc",
    "qr",
    "pin",
    "mobile",
  ]).default("fingerprint"),
  protocol: z.enum([
    "push_adms",
    "generic_http",
    "mqtt",
    "pull_sdk",
    "simulator",
  ]).default("push_adms"),
  ip_address: z.string().max(64).optional().or(z.literal("")),
  port: z.coerce.number().min(0).max(65535).optional(),
  location: z.string().max(100).optional().or(z.literal("")),
  branch: z.string().optional().or(z.literal("")),
  is_active: z.boolean().default(true),
});

export type DeviceTerminalFormData = z.infer<typeof deviceTerminalSchema>;

export const resolveUnmappedSchema = z.object({
  user_type: z.enum(["student", "staff"]),
  student_id: z.string().optional(),
  staff_id: z.string().optional(),
});

export type ResolveUnmappedFormData = z.infer<typeof resolveUnmappedSchema>;
