export type UserRole = 'admin' | 'editor' | 'reader';

export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  is_2fa_enabled: boolean;
  created_at: string;
  last_login: string | null;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page?: number;
  limit?: number;
  pages?: number;
}

export interface UserUpdate {
  role?: UserRole;
  is_active?: boolean;
  first_name?: string;
  last_name?: string;
}
