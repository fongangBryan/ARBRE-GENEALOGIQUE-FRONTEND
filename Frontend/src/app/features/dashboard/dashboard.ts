import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';

const API = 'http://localhost:8090/api/v1';

interface Person {
  id: string;
  first_name: string;
  last_name: string;
  birth_date?: string | null;
  gender?: string;
}

interface PersonListResponse {
  items: Person[];
  total: number;
}

interface MediaItem {
  id: string;
  mime_type: string;
  thumbnail_key?: string | null;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit {
  private http = inject(HttpClient);
  readonly auth = inject(AuthService);

  loading        = signal(true);
  persons        = signal<Person[]>([]);
  totalPersons   = signal(0);
  sidebarOpen    = signal(false);
  photos         = signal<MediaItem[]>([]);
  loadingPhotos  = signal(false);

  readonly isEditor = computed(() => {
    const role = this.auth.currentUser()?.role;
    return role === 'editor' || role === 'admin';
  });

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
        const slice = data.items.slice(0, 6);
        this.persons.set(slice);
        this.loading.set(false);
        this.loadPhotos(slice);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadPhotos(persons: Person[]) {
    if (!persons.length) return;
    this.loadingPhotos.set(true);
    const reqs = persons.slice(0, 4).map(p =>
      this.http.get<MediaItem[]>(`${API}/media/owner/person/${p.id}`).pipe(
        catchError(() => of([] as MediaItem[]))
      )
    );
    forkJoin(reqs).pipe(
      map(results => results.flat().filter(m => m.mime_type?.startsWith('image/')).slice(0, 8))
    ).subscribe({
      next: items => { this.photos.set(items); this.loadingPhotos.set(false); },
      error: () => this.loadingPhotos.set(false),
    });
  }

  photoSrc(m: MediaItem): string {
    return m.thumbnail_key
      ? `${API}/media/${m.id}/thumbnail`
      : `${API}/media/${m.id}`;
  }

  formatBirthDate(raw: string | null | undefined): string {
    if (!raw) return 'Date inconnue';
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
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

  getUserEmail(): string { return this.auth.currentUser()?.email ?? ''; }

  getUserRole(): string {
    const role = this.auth.currentUser()?.role ?? 'editor';
    return role.charAt(0).toUpperCase() + role.slice(1);
  }
}
