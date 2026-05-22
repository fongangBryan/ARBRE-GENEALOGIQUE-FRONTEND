import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { AppShellComponent } from '../../shared/components/app-shell/app-shell';
import { PersonService } from '../../services/person.service';
import { Person, PersonCreate, Gender } from '../../models/person.model';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-persons',
  standalone: true,
  imports: [AppShellComponent, FormsModule, ReactiveFormsModule, RouterLink],
  templateUrl: './persons.html',
  styleUrl: './persons.css',
})
export class PersonsComponent implements OnInit {
  private svc   = inject(PersonService);
  private fb    = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  readonly auth = inject(AuthService);

  persons     = signal<Person[]>([]);
  total       = signal(0);
  page        = signal(1);
  totalPages  = signal(1);
  pageSize    = 20;
  loading     = signal(true);
  saving      = signal(false);
  error       = signal<string | null>(null);
  success     = signal<string | null>(null);
  searchQuery = signal('');
  searchTimer: ReturnType<typeof setTimeout> | null = null;

  modalMode    = signal<'create' | 'edit' | null>(null);
  editTarget   = signal<Person | null>(null);
  deleteTarget = signal<Person | null>(null);

  readonly isEditor = computed(() => {
    const role = this.auth.currentUser()?.role;
    return role === 'editor' || role === 'admin';
  });

  readonly isAdmin = computed(() => this.auth.currentUser()?.role === 'admin');

  form = this.fb.group({
    first_name:    ['', [Validators.required, Validators.minLength(1)]],
    last_name:     ['', [Validators.required, Validators.minLength(1)]],
    maiden_name:   [''],
    gender:        [''],
    birth_date:    [''],
    birth_place:   [''],
    death_date:    [''],
    death_place:   [''],
    is_living:     [true],
    occupation:    [''],
    nationality:   [''],
    biography:     [''],
    privacy_level: ['private'],
  });

  ngOnInit() {
    if (!this.auth.currentUser()) this.auth.fetchCurrentUser().subscribe();
    this.load();
    if (this.route.snapshot.queryParamMap.get('create') === 'true') {
      this.openCreate();
    }
  }

  load(p = 1) {
    this.loading.set(true);
    this.svc.list(p, this.pageSize, this.searchQuery()).subscribe({
      next: res => {
        this.persons.set(res.items);
        this.total.set(res.total);
        this.page.set(p);
        this.totalPages.set(res.pages);
        this.loading.set(false);
      },
      error: () => { this.error.set('Impossible de charger les membres.'); this.loading.set(false); },
    });
  }

  onSearch() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.load(1), 350);
  }

  openCreate() {
    this.form.reset({ is_living: true, privacy_level: 'private' });
    this.editTarget.set(null);
    this.modalMode.set('create');
  }

  openEdit(p: Person) {
    this.editTarget.set(p);
    this.form.patchValue({
      first_name: p.first_name, last_name: p.last_name,
      maiden_name: p.maiden_name ?? '', gender: p.gender ?? '',
      birth_date: p.birth_date ?? '', birth_place: p.birth_place ?? '',
      death_date: p.death_date ?? '', death_place: p.death_place ?? '',
      is_living: p.is_living, occupation: p.occupation ?? '',
      nationality: p.nationality ?? '', biography: p.biography ?? '',
      privacy_level: p.privacy_level,
    });
    this.modalMode.set('edit');
  }

  closeModal() { this.modalMode.set(null); }

  saveForm() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    const raw = this.form.getRawValue();
    const payload: PersonCreate = {
      first_name: raw.first_name!,
      last_name:  raw.last_name!,
      maiden_name: raw.maiden_name || undefined,
      gender: (raw.gender as Gender) || undefined,
      birth_date:  raw.birth_date  || undefined,
      birth_place: raw.birth_place || undefined,
      death_date:  raw.death_date  || undefined,
      death_place: raw.death_place || undefined,
      is_living:   !!raw.is_living,
      occupation:  raw.occupation  || undefined,
      nationality: raw.nationality || undefined,
      biography:   raw.biography   || undefined,
      privacy_level: (raw.privacy_level as any) || 'private',
    };

    const obs = this.editTarget()
      ? this.svc.update(this.editTarget()!.id, payload)
      : this.svc.create(payload);

    obs.subscribe({
      next: saved => {
        if (this.editTarget()) {
          this.persons.update(list => list.map(p => p.id === saved.id ? saved : p));
          this.flash('Membre modifié.');
        } else {
          this.persons.update(list => [saved, ...list]);
          this.total.update(n => n + 1);
          this.flash('Membre ajouté.');
        }
        this.closeModal();
        this.saving.set(false);
      },
      error: err => {
        this.saving.set(false);
        this.error.set(err.error?.detail ?? 'Erreur lors de la sauvegarde.');
      },
    });
  }

  openDelete(p: Person) { this.deleteTarget.set(p); }
  closeDelete() { this.deleteTarget.set(null); }

  confirmDelete() {
    const p = this.deleteTarget();
    if (!p) return;
    this.saving.set(true);
    this.svc.delete(p.id).subscribe({
      next: () => {
        this.persons.update(list => list.filter(x => x.id !== p.id));
        this.total.update(n => n - 1);
        this.closeDelete();
        this.saving.set(false);
        this.flash('Membre supprimé.');
      },
      error: () => { this.saving.set(false); this.error.set('Erreur lors de la suppression.'); },
    });
  }

  private flash(msg: string) {
    this.success.set(msg);
    setTimeout(() => this.success.set(null), 3000);
  }

  prevPage() { if (this.page() > 1) this.load(this.page() - 1); }
  nextPage() { if (this.page() < this.totalPages()) this.load(this.page() + 1); }

  pages(): number[] {
    const t = this.totalPages(), c = this.page();
    const r: number[] = [];
    for (let i = Math.max(1, c - 2); i <= Math.min(t, c + 2); i++) r.push(i);
    return r;
  }

  initials(p: Person) {
    return `${p.first_name[0] ?? ''}${p.last_name[0] ?? ''}`.toUpperCase();
  }

  genderIcon(g?: string | null) {
    if (g === 'male')   return '♂';
    if (g === 'female') return '♀';
    return '—';
  }
}
