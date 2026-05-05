import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { AppShellComponent } from '../../shared/components/app-shell/app-shell';
import { UnionService } from '../../services/union.service';
import { PersonService } from '../../services/person.service';
import { Union, UnionCreate, UnionType, UnionStatut } from '../../models/union.model';
import { Person } from '../../models/person.model';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-unions',
  standalone: true,
  imports: [AppShellComponent, FormsModule, ReactiveFormsModule],
  templateUrl: './unions.html',
  styleUrl: './unions.css',
})
export class UnionsComponent implements OnInit {
  private svc   = inject(UnionService);
  private pSvc  = inject(PersonService);
  private fb    = inject(FormBuilder);
  readonly auth = inject(AuthService);

  persons      = signal<Person[]>([]);
  selectedPid  = signal('');
  unions       = signal<Union[]>([]);
  loading      = signal(false);
  saving       = signal(false);
  error        = signal<string | null>(null);
  success      = signal<string | null>(null);
  modalMode    = signal<'create' | 'edit' | null>(null);
  editTarget   = signal<Union | null>(null);
  deleteTarget = signal<Union | null>(null);

  readonly isEditor = computed(() => {
    const role = this.auth.currentUser()?.role;
    return role === 'editor' || role === 'admin';
  });

  readonly personMap = computed(() => {
    const m = new Map<string, Person>();
    this.persons().forEach(p => m.set(p.id, p));
    return m;
  });

  form = this.fb.group({
    person_id_1:      ['', Validators.required],
    person_id_2:      ['', Validators.required],
    union_type:       ['mariage'],
    date_union:       [''],
    lieu_union:       [''],
    date_dissolution: [''],
    statut:           ['actif'],
  });

  ngOnInit() {
    if (!this.auth.currentUser()) this.auth.fetchCurrentUser().subscribe();
    this.pSvc.list(1, 200).subscribe({ next: r => this.persons.set(r.items) });
  }

  loadUnions() {
    const id = this.selectedPid();
    if (!id) { this.unions.set([]); return; }
    this.loading.set(true);
    this.svc.getByPerson(id).subscribe({
      next: list => { this.unions.set(list); this.loading.set(false); },
      error: () => { this.error.set('Impossible de charger les unions.'); this.loading.set(false); }
    });
  }

  personName(id: string): string {
    const p = this.personMap().get(id);
    return p ? `${p.first_name} ${p.last_name}` : '—';
  }

  partnerOf(u: Union): string {
    const ref = this.selectedPid();
    return this.personName(u.person_id_1 === ref ? u.person_id_2 : u.person_id_1);
  }

  availablePartners(): Person[] {
    const ref = this.form.get('person_id_1')?.value;
    return this.persons().filter(p => p.id !== ref);
  }

  typeLabel(t: string): string {
    const m: Record<string, string> = { mariage: 'Mariage', union_libre: 'Union libre', pacs: 'PACS', fiancailles: 'Fiançailles' };
    return m[t] ?? t;
  }

  openCreate() {
    this.form.reset({ person_id_1: this.selectedPid(), union_type: 'mariage', statut: 'actif' });
    this.editTarget.set(null);
    this.modalMode.set('create');
  }

  openEdit(u: Union) {
    this.editTarget.set(u);
    this.form.patchValue({
      person_id_1: u.person_id_1, person_id_2: u.person_id_2,
      union_type: u.union_type,
      date_union: u.date_union ?? '',
      lieu_union: u.lieu_union ?? '',
      date_dissolution: u.date_dissolution ?? '',
      statut: u.statut,
    });
    this.modalMode.set('edit');
  }

  closeModal() { this.modalMode.set(null); }
  openDelete(u: Union)  { this.deleteTarget.set(u); }
  closeDelete()         { this.deleteTarget.set(null); }

  save() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving.set(true);
    const v = this.form.getRawValue();
    const payload: UnionCreate = {
      person_id_1: v.person_id_1!,
      person_id_2: v.person_id_2!,
      union_type:  (v.union_type as UnionType) || 'mariage',
      date_union:  v.date_union  || undefined,
      lieu_union:  v.lieu_union  || undefined,
      date_dissolution: v.date_dissolution || undefined,
      statut: (v.statut as UnionStatut) || 'actif',
    };

    const obs = this.editTarget()
      ? this.svc.update(this.editTarget()!.id, payload)
      : this.svc.create(payload);

    obs.subscribe({
      next: saved => {
        if (this.editTarget()) {
          this.unions.update(list => list.map(x => x.id === saved.id ? saved : x));
          this.flash('Union modifiée avec succès.');
        } else {
          this.unions.update(list => [saved, ...list]);
          this.flash('Union créée avec succès.');
        }
        this.closeModal();
        this.saving.set(false);
      },
      error: err => {
        this.saving.set(false);
        this.error.set(err.error?.detail ?? 'Erreur lors de la sauvegarde.');
      }
    });
  }

  confirmDelete() {
    const u = this.deleteTarget();
    if (!u) return;
    this.saving.set(true);
    this.svc.delete(u.id).subscribe({
      next: () => {
        this.unions.update(list => list.filter(x => x.id !== u.id));
        this.closeDelete();
        this.saving.set(false);
        this.flash('Union supprimée.');
      },
      error: () => { this.saving.set(false); this.error.set('Erreur lors de la suppression.'); }
    });
  }

  private flash(msg: string) {
    this.success.set(msg);
    setTimeout(() => this.success.set(null), 3000);
  }
}
