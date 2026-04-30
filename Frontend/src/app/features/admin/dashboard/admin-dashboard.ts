import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { AdminService } from '../../../services/admin.service';
import { User, UserRole } from '../../../models/user.model';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, FormsModule, DatePipe],
  templateUrl: './admin-dashboard.html',
  styleUrl: './admin-dashboard.css',
})
export class AdminDashboardComponent implements OnInit {
  readonly auth  = inject(AuthService);
  private admin  = inject(AdminService);

  sidebarOpen = signal(false);
  loading     = signal(true);
  saving      = signal(false);
  error       = signal<string | null>(null);
  successMsg  = signal<string | null>(null);

  users       = signal<User[]>([]);
  totalUsers  = signal(0);
  currentPage = signal(1);
  totalPages  = signal(1);
  pageSize    = 20;

  searchQuery  = signal('');
  searchDebounce: ReturnType<typeof setTimeout> | null = null;

  editingUser  = signal<User | null>(null);
  editRole     = signal<UserRole>('editor');
  editActive   = signal(true);

  deleteTarget = signal<User | null>(null);

  stats = computed(() => {
    const all = this.users();
    return {
      total:   this.totalUsers(),
      active:  all.filter(u => u.is_active).length,
      admins:  all.filter(u => u.role === 'admin').length,
      editors: all.filter(u => u.role === 'editor').length,
      readers: all.filter(u => u.role === 'reader').length,
    };
  });

  ngOnInit() {
    if (!this.auth.currentUser()) {
      this.auth.fetchCurrentUser().subscribe();
    }
    this.loadUsers();
  }

  loadUsers(page = 1) {
    this.loading.set(true);
    this.error.set(null);
    this.admin.listUsers(page, this.pageSize, this.searchQuery()).subscribe({
      next: res => {
        this.users.set(res.items);
        this.totalUsers.set(res.total);
        this.currentPage.set(page);
        this.totalPages.set(res.pages ?? Math.ceil(res.total / this.pageSize));
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les utilisateurs.');
        this.loading.set(false);
      },
    });
  }

  onSearch() {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => this.loadUsers(1), 350);
  }

  openEdit(user: User) {
    this.editingUser.set(user);
    this.editRole.set(user.role);
    this.editActive.set(user.is_active);
  }

  closeEdit() { this.editingUser.set(null); }

  saveEdit() {
    const user = this.editingUser();
    if (!user) return;
    this.saving.set(true);

    const roleChanged   = this.editRole()   !== user.role;
    const activeChanged = this.editActive() !== user.is_active;

    const roleObs   = roleChanged   ? this.admin.updateRole(user.id, this.editRole()) : null;
    const activeObs = activeChanged ? this.admin.toggleActive(user.id, user.is_active) : null;

    const done = (updatedUser?: User) => {
      if (updatedUser) {
        this.users.update(list => list.map(u => u.id === updatedUser.id ? updatedUser : u));
      } else if (activeChanged) {
        // activate/deactivate returns {message}, reload the row
        this.users.update(list => list.map(u =>
          u.id === user.id ? { ...u, role: this.editRole(), is_active: this.editActive() } : u
        ));
      }
      this.closeEdit();
      this.saving.set(false);
      this.flash('Utilisateur mis à jour avec succès.');
    };

    const fail = () => { this.saving.set(false); this.error.set('Erreur lors de la mise à jour.'); };

    if (roleObs && activeObs) {
      roleObs.subscribe({
        next: updated => activeObs.subscribe({ next: () => done(updated), error: fail }),
        error: fail,
      });
    } else if (roleObs) {
      roleObs.subscribe({ next: done, error: fail });
    } else if (activeObs) {
      activeObs.subscribe({ next: () => done(), error: fail });
    } else {
      this.closeEdit();
      this.saving.set(false);
    }
  }

  toggleActive(user: User) {
    this.admin.toggleActive(user.id, user.is_active).subscribe({
      next: () => {
        const nowActive = !user.is_active;
        this.users.update(list => list.map(u =>
          u.id === user.id ? { ...u, is_active: nowActive } : u
        ));
        this.flash(nowActive ? 'Utilisateur activé.' : 'Utilisateur désactivé.');
      },
      error: () => this.error.set('Erreur lors de la mise à jour.'),
    });
  }

  openDelete(user: User) { this.deleteTarget.set(user); }
  closeDelete() { this.deleteTarget.set(null); }

  confirmDelete() {
    const user = this.deleteTarget();
    if (!user) return;
    this.saving.set(true);
    this.admin.deleteUser(user.id).subscribe({
      next: () => {
        this.users.update(list => list.filter(u => u.id !== user.id));
        this.totalUsers.update(n => n - 1);
        this.closeDelete();
        this.saving.set(false);
        this.flash('Utilisateur supprimé.');
      },
      error: () => {
        this.saving.set(false);
        this.error.set('Erreur lors de la suppression.');
      },
    });
  }

  private flash(msg: string) {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(null), 3500);
  }

  prevPage() { if (this.currentPage() > 1) this.loadUsers(this.currentPage() - 1); }
  nextPage() { if (this.currentPage() < this.totalPages()) this.loadUsers(this.currentPage() + 1); }

  logout() { this.auth.logout(); }
  toggleSidebar() { this.sidebarOpen.update(v => !v); }

  getUserInitials(): string {
    const user = this.auth.currentUser();
    if (user?.first_name || user?.last_name) {
      return `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase();
    }
    return user?.email?.slice(0, 2).toUpperCase() ?? 'AD';
  }

  getUserEmail(): string { return this.auth.currentUser()?.email ?? ''; }

  roleLabel(role: UserRole): string {
    return { admin: 'Admin', editor: 'Éditeur', reader: 'Lecteur' }[role];
  }

  roleClass(role: UserRole): string {
    return { admin: 'badge-admin', editor: 'badge-editor', reader: 'badge-reader' }[role];
  }

  getInitials(u: User): string {
    return `${u.first_name?.[0] ?? ''}${u.last_name?.[0] ?? u.email[0]}`.toUpperCase();
  }

  pages(): number[] {
    const total = this.totalPages();
    const cur   = this.currentPage();
    const delta = 2;
    const range: number[] = [];
    for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) range.push(i);
    return range;
  }
}
