import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { User, UserListResponse, UserRole } from '../models/user.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);

  listUsers(page = 1, limit = 20, search?: string) {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('limit', limit.toString());
    if (search?.trim()) params = params.set('search', search.trim());
    return this.http.get<UserListResponse>(`${API}/admin/users`, { params });
  }

  getUser(id: string) {
    return this.http.get<User>(`${API}/admin/users/${id}`);
  }

  updateRole(id: string, role: UserRole) {
    return this.http.put<User>(`${API}/admin/users/${id}/role`, { role });
  }

  activate(id: string) {
    return this.http.post<{ message: string }>(`${API}/admin/users/${id}/activate`, {});
  }

  deactivate(id: string) {
    return this.http.post<{ message: string }>(`${API}/admin/users/${id}/deactivate`, {});
  }

  toggleActive(id: string, currentlyActive: boolean) {
    return currentlyActive ? this.deactivate(id) : this.activate(id);
  }

  deleteUser(id: string) {
    return this.http.delete<void>(`${API}/admin/users/${id}`);
  }

  getVerificationLink(id: string) {
    return this.http.post<{ link: string; expires_hours: number }>(`${API}/admin/users/${id}/verification-link`, {});
  }

  getResetLink(id: string) {
    return this.http.post<{ link: string; expires_minutes: number }>(`${API}/admin/users/${id}/reset-link`, {});
  }

  getAuditLogs(page = 1, limit = 50, userId?: string, action?: string) {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('limit', limit.toString());
    if (userId) params = params.set('user_id', userId);
    if (action) params = params.set('action', action);
    return this.http.get<AuditLogResponse>(`${API}/admin/logs`, { params });
  }
}

export interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
  user: { email: string; first_name: string | null; last_name: string | null } | null;
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  pages: number;
}

