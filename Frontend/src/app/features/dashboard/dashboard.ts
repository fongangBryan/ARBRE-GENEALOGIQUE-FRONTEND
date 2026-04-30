import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { AuthService } from '../../services/auth.service';

const API = 'http://localhost:8080/api/v1';

interface Person {
  id: number;
  first_name: string;
  last_name: string;
  birth_date?: string | null;
  gender?: string;
}

interface PersonListResponse {
  items: Person[];
  total: number;
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

  ngOnInit() {
    if (!this.auth.currentUser()) {
      this.auth.fetchCurrentUser().subscribe();
    }
    this.loadData();
  }

  private loadData() {
    this.http.get<PersonListResponse>(`${API}/persons/`).subscribe({
      next: data => {
        this.totalPersons.set(data.total);
        this.persons.set(data.items.slice(0, 6));
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
    const user = this.auth.currentUser();
    if (user?.first_name || user?.last_name) {
      return `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase();
    }
    return user?.email?.slice(0, 2).toUpperCase() ?? 'U';
  }

  getUserEmail(): string {
    return this.auth.currentUser()?.email ?? '';
  }

  getUserRole(): string {
    const role = this.auth.currentUser()?.role ?? 'editor';
    return role.charAt(0).toUpperCase() + role.slice(1);
  }
}
