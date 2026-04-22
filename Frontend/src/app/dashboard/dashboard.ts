import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { AuthService } from '../core/services/auth.service';

const API = 'http://localhost:8000/api/v1';

interface Person {
  id: number;
  first_name: string;
  last_name: string;
  birth_date?: string | null;
  gender?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, DatePipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit {
  private http = inject(HttpClient);
  readonly auth = inject(AuthService);

  loading      = signal(true);
  persons      = signal<Person[]>([]);
  totalPersons = signal(0);
  sidebarOpen  = signal(false);

  ngOnInit() { this.loadData(); }

  private loadData() {
    this.http.get<Person[]>(`${API}/persons/`).subscribe({
      next: data => {
        this.totalPersons.set(data.length);
        this.persons.set(data.slice(0, 6));
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  logout() { this.auth.logout(); }
  toggleSidebar() { this.sidebarOpen.update(v => !v); }

  getInitials(first: string, last: string): string {
    return `${first?.[0] ?? ''}${last?.[0] ?? ''}`.toUpperCase();
  }

  getUserInitials(): string {
    const payload = this.decodeToken();
    if (!payload) return 'U';
    const email: string = payload.sub ?? '';
    return email.slice(0, 2).toUpperCase();
  }

  getUserEmail(): string {
    return this.decodeToken()?.sub ?? 'utilisateur';
  }

  private decodeToken(): any {
    const token = this.auth.getToken();
    if (!token) return null;
    try { return JSON.parse(atob(token.split('.')[1])); } catch { return null; }
  }
}
