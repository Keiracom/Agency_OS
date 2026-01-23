/**
 * Settings Components - Prototype components for Agency OS settings pages
 *
 * This module exports all settings-related components for the dashboard prototype.
 * All components use "use client" directive, Tailwind CSS, and lucide-react icons.
 * Components use static demo data - no real API calls.
 */

// Base Components
export { EmergencyPauseButton } from "./EmergencyPauseButton";
export type { EmergencyPauseButtonProps } from "./EmergencyPauseButton";

export { IntegrationStatusCard } from "./IntegrationStatusCard";
export type { IntegrationStatusCardProps, IntegrationStatus } from "./IntegrationStatusCard";

export { TimezoneSelector } from "./TimezoneSelector";
export type { TimezoneSelectorProps } from "./TimezoneSelector";

export { NotificationSettingsForm } from "./NotificationSettingsForm";
export type { NotificationSettingsFormProps, NotificationPreferences } from "./NotificationSettingsForm";

export { ProfileSettingsForm } from "./ProfileSettingsForm";
export type { ProfileSettingsFormProps, ClientProfile } from "./ProfileSettingsForm";

export { ICPSettingsForm } from "./ICPSettingsForm";
export type { ICPSettingsFormProps, ICPProfile } from "./ICPSettingsForm";

export { LinkedInStatusCard } from "./LinkedInStatusCard";
export type { LinkedInStatusCardProps, LinkedInStatus } from "./LinkedInStatusCard";

// Page Components
export { SettingsHub } from "./SettingsHub";
export { ICPSettings } from "./ICPSettings";
export { LinkedInSettings } from "./LinkedInSettings";
export { ProfileSettings } from "./ProfileSettings";
export { NotificationSettings } from "./NotificationSettings";
