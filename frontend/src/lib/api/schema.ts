export type RoleAssignment = {
  role: string;
  scope_type: string;
  scope_id: string | null;
};

export type UserMe = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  locale: string;
  timezone: string;
  email_verified_at: string | null;
  roles: RoleAssignment[];
  permissions: string[];
  is_staff: boolean;
};

export type BrandSettings = {
  org_name: string;
  logo_url: string;
  favicon_url: string;
  primary_color: string;
  accent_color: string;
  background_color: string;
  foreground_color: string;
  ink_color: string;
  ink2_color: string;
  ink_foreground: string;
  font_display: string;
  font_ui: string;
  extra_css_vars: Record<string, string>;
};

export type LoginResponse = {
  access: string;
  user: UserMe;
};

export type ApiError = {
  code: string;
  message: string;
  fields: Record<string, unknown>;
  request_id: string | null;
};
