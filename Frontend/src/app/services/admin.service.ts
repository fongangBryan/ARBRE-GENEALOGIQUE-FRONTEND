import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { User, UserListResponse, UserRole } from '../models/user.model';

const API = 'http://localhost:8080/api/v1';

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
}
