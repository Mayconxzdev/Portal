export interface ModulePermission {
  module_id: number;
  module_code: string;
  module_name: string;
  permission_level: string;
}

export interface UserItem {
  id: number;
  username: string;
  email?: string | null;
  full_name?: string | null;
  department?: string | null;
  job_title?: string | null;
  role_id: number | null;
  role_name: string | null;
  is_active: boolean;
  must_change_password?: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
  module_permissions: ModulePermission[];
}

export interface RoleItem {
  id: number;
  name: string;
  description: string | null;
}

export interface ModuleItem {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  is_restricted: boolean;
}

export interface AuditLogItem {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  module: string;
  details: any;
  ip_address: string | null;
  created_at: string;
}

export interface AdminSessionItem {
  id: number;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  revoked_at?: string | null;
  revocation_reason?: string | null;
  is_active: boolean;
}

export interface AdminTemporaryAccessItem {
  id: number;
  module_id: number;
  module_code: string;
  module_name: string;
  permission_level: string;
  reason: string;
  starts_at: string;
  expires_at: string;
  status: string;
  revoked_at?: string | null;
  revocation_reason?: string | null;
  is_effective: boolean;
}

export interface AdminTemporarySubstitutionItem {
  id: number;
  substitute_user_id: number;
  substitute_username: string;
  reason: string;
  starts_at: string;
  expires_at: string;
  status: string;
  ended_at?: string | null;
  is_effective: boolean;
}

export interface AdminOffboardingImpactItem {
  key: string;
  label: string;
  count: number;
  action: string;
  can_auto_apply: boolean;
}

export interface AdminOffboardingImpact {
  target_user: {
    id: number;
    username: string;
    full_name?: string | null;
    email?: string | null;
    is_active: boolean;
  };
  items: AdminOffboardingImpactItem[];
  requires_human_review: boolean;
  generated_at: string;
}

export interface AdminOffboardingCase {
  id: number;
  status: string;
  reason: string;
  replacement_user_id?: number | null;
  impact_snapshot: AdminOffboardingImpact;
  tasks: Array<{
    id: number;
    title: string;
    description: string;
    status: string;
    requires_human_review: boolean;
  }>;
}

export interface AccessProfilePreset {
  id: string;
  label: string;
  roleNames: string[];
  description: string;
  purpose: string;
  risk: 'Baixo' | 'Medio' | 'Alto' | 'Critico';
  accessLevelByModule: Record<string, string>;
  positive: string[];
  negative: string[];
  warnings?: string[];
}
