import { Component, Input, inject, signal, computed } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.css',
})
export class AppShellComponent {
  @Input() pageTitle  = '';
  @Input() pageSubtitle = '';

  readonly auth = inject(AuthService);
  sidebarOpen = signal(false);

  readonly isEditor = computed(() => {
    const role = this.auth.currentUser()?.role;
    return role === 'editor' || role === 'admin';
  });

  toggleSidebar() { this.sidebarOpen.update(v => !v); }

  logout() { this.auth.logout(); }

  getUserInitials(): string {
    const u = this.auth.currentUser();
    if (u?.first_name || u?.last_name)
      return `${u.first_name?.[0] ?? ''}${u.last_name?.[0] ?? ''}`.toUpperCase();
    return u?.email?.slice(0, 2).toUpperCase() ?? 'U';
  }

  getUserEmail()  { return this.auth.currentUser()?.email ?? ''; }
  getUserRole()   {
    const r = this.auth.currentUser()?.role ?? 'editor';
    return r.charAt(0).toUpperCase() + r.slice(1);
  }
}
