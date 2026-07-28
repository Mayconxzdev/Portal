export interface CurrentUser {
  id: number;
  username: string;
  role: string;
  module_permissions: Record<string, string>;
}

export interface KanbanLabel {
  id: number;
  board_id: number;
  name: string;
  color: string;
  is_active: boolean;
}

export interface CardAssignee {
  id: number;
  card_id: number;
  user_id: number;
  assigned_by_user_id: number;
  created_at: string;
  user?: { id: number; username: string; email?: string };
}

export interface KanbanCard {
  id: number;
  board_id: number;
  column_id: number;
  title: string;
  description?: string;
  position: number;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status?: string;
  due_date?: string;
  assigned_to_user_id?: number;
  custom_fields?: Record<string, unknown>;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  labels: KanbanLabel[];
  assignees: CardAssignee[];
  checklist_total: number;
  checklist_done: number;
  urgency_score?: number;
  urgency_reasons?: string[];
}

export interface KanbanColumn {
  id: number;
  board_id: number;
  name: string;
  position: number;
  color?: string;
  wip_limit?: number;
  is_done_column: boolean;
  is_archived: boolean;
  cards: KanbanCard[];
}

export interface CustomField {
  id: number;
  board_id: number;
  name: string;
  key: string;
  field_type: string;
  options?: Record<string, unknown>;
  is_required: boolean;
  is_active: boolean;
  position: number;
}

export interface BoardViewConfig {
  id: number;
  board_id: number;
  name: string;
  view_type: 'BOARD' | 'LIST' | 'TV_BOARD' | 'TV_LIST' | 'PRODUCTION_LIST' | 'PRODUCTION_BOARD';
  is_default: boolean;
  density: 'COMFORTABLE' | 'COMPACT' | 'DENSE';
  visible_columns?: string[];
  column_order?: string[];
  column_widths?: Record<string, number>;
  filters?: Record<string, unknown>;
  sort_by?: string;
  group_by?: string;
  color_rules?: Record<string, unknown>;
  font_scale?: string;
  auto_scroll: boolean;
  auto_scroll_seconds?: number;
}

export interface KanbanBoard {
  id: number;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  icon?: string;
  is_archived: boolean;
  access_level?: 'READ_ONLY' | 'NORMAL' | 'MANAGER' | 'ADMIN';
  columns: KanbanColumn[];
  custom_fields: CustomField[];
  labels: KanbanLabel[];
  views: BoardViewConfig[];
}

export interface BoardPermission {
  id: number;
  board_id: number;
  user_id?: number;
  role_id?: number;
  access_level: 'NO_ACCESS' | 'READ_ONLY' | 'NORMAL' | 'MANAGER' | 'ADMIN';
  username?: string;
  user_email?: string;
  role_name?: string;
}

export interface UserOption {
  id: number;
  username: string;
  email?: string;
}

export interface RoleOption {
  id: number;
  name: string;
  description?: string;
}

export interface ListData {
  board: KanbanBoard;
  cards: Array<KanbanCard & { status?: string; urgency_score?: number; urgency_reasons?: string[] }>;
  columns: KanbanColumn[];
  labels: KanbanLabel[];
  custom_fields: CustomField[];
  views: BoardViewConfig[];
  list_config?: BoardViewConfig;
  visible_columns: string[];
  column_order?: string[];
  column_widths?: Record<string, number>;
  generated_at: string;
}

export interface Activity {
  id: number;
  action: string;
  card_id?: number;
  actor_user_id?: number;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ChecklistItem {
  id: number;
  checklist_id: number;
  text: string;
  is_done: boolean;
  position: number;
}

export interface Checklist {
  id: number;
  card_id: number;
  title: string;
  position: number;
  items: ChecklistItem[];
}

export interface CardComment {
  id: number;
  card_id: number;
  user_id: number;
  comment: string;
  created_at: string;
  edited_at?: string;
}

export interface CardAttachment {
  id: number;
  card_id: number;
  file_id: number;
  uploaded_by_user_id: number;
  created_at: string;
  file?: {
    original_filename: string;
    content_type: string;
    size_bytes: number;
  };
}

export interface TVConfig {
  id?: number | null;
  board_id: number;
  name: string;
  is_default: boolean;
  layout_type: 'COLUMNS' | 'URGENCY' | 'PRODUCTION' | 'COMPACT' | 'TV_LIST' | 'PRODUCTION_LIST';
  refresh_interval_seconds: number;
  show_archived: boolean;
  show_done_columns: boolean;
  show_checklist_progress: boolean;
  show_assignees: boolean;
  show_labels: boolean;
  show_due_date: boolean;
  show_card_description: boolean;
  group_by?: string;
  sort_by?: string;
  filters?: Record<string, unknown>;
  visible_custom_fields?: string[];
  display_options?: Record<string, any>;
  kpi_options?: Record<string, any>;
  layout_options?: Record<string, any>;
  external_mode_options?: Record<string, any>;
}

export interface TVData {
  board: KanbanBoard;
  columns: KanbanColumn[];
  cards: KanbanCard[];
  metrics: Record<string, any>;
  critical_cards: Array<Record<string, any>>;
  generated_at: string;
  connection_mode: string;
  config: TVConfig;
  production_fields: string[];
}

export interface SearchResult {
  type: 'module' | 'board' | 'card' | 'approval' | 'tv' | 'supplier' | 'product' | 'it_ticket' | 'it_asset' | 'credential' | 'proposal' | 'nas_file';
  id: string | number;
  board_id?: number;
  title: string;
  subtitle: string;
  action: string;
}
