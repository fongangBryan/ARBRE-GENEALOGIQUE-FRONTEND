import {
  Component, inject, signal, OnInit, computed,
  ElementRef, ViewChild
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { forkJoin, Observable } from 'rxjs';
import { AppShellComponent } from '../../../shared/components/app-shell/app-shell';
import { PersonService } from '../../../services/person.service';
import { FiliationService } from '../../../services/filiation.service';
import { UnionService } from '../../../services/union.service';
import { MediaService } from '../../../services/media.service';
import { EventService } from '../../../services/event.service';
import { TagService } from '../../../services/tag.service';
import { AuthService } from '../../../services/auth.service';
import { Person, PersonCreate } from '../../../models/person.model';
import { Filiation, FiliationType } from '../../../models/filiation.model';
import { Union, UnionType, UnionStatut } from '../../../models/union.model';
import { Media } from '../../../models/media.model';
import { LifeEvent, EventType } from '../../../models/event.model';
import { Tag } from '../../../models/tag.model';

type Tab = 'profile' | 'family' | 'media' | 'events';
type DelType = 'filiation-parent' | 'filiation-child' | 'union' | 'media' | 'event';

@Component({
  selector: 'app-person-detail',
  standalone: true,
  imports: [AppShellComponent, FormsModule, ReactiveFormsModule, RouterLink],
  templateUrl: './person-detail.html',
  styleUrl:    './person-detail.css',
})
export class PersonDetailComponent implements OnInit {
  @ViewChild('uploadInput') uploadInputRef!: ElementRef<HTMLInputElement>;

  private route     = inject(ActivatedRoute);
  private personSvc = inject(PersonService);
  private filSvc    = inject(FiliationService);
  private unionSvc  = inject(UnionService);
  private mediaSvc  = inject(MediaService);
  private eventSvc  = inject(EventService);
  private tagSvc    = inject(TagService);
  private fb        = inject(FormBuilder);
  readonly auth     = inject(AuthService);

  person     = signal<Person | null>(null);
  parents    = signal<Filiation[]>([]);
  children   = signal<Filiation[]>([]);
  unions     = signal<Union[]>([]);
  media      = signal<Media[]>([]);
  events     = signal<LifeEvent[]>([]);
  allPersons = signal<Person[]>([]);
  personTags = signal<Tag[]>([]);
  allTags    = signal<Tag[]>([]);

  loading        = signal(true);
  saving         = signal(false);
  uploading      = signal(false);
  uploadProgress = signal(0);
  error          = signal<string | null>(null);
  success        = signal<string | null>(null);

  activeTab      = signal<Tab>('profile');
  editModal      = signal(false);
  tagPickerOpen  = signal(false);
  newTagLabel    = signal('');
  newTagColor    = signal('#02E08E');
  savingTag      = signal(false);
  filiationModal = signal(false);
  filiationRole  = signal<'parent' | 'child'>('parent');
  unionModal     = signal(false);
  unionEditTarget = signal<Union | null>(null);
  eventModal     = signal(false);
  eventEditTarget = signal<LifeEvent | null>(null);
  deleteModal    = signal<{ dtype: DelType; id: string; label: string } | null>(null);

  readonly isEditor = computed(() => {
    const r = this.auth.currentUser()?.role;
    return r === 'editor' || r === 'admin';
  });

  readonly personMap = computed(() => {
    const m = new Map<string, Person>();
    this.allPersons().forEach(p => m.set(p.id, p));
    return m;
  });

  readonly availableTags = computed(() => {
    const assigned = new Set(this.personTags().map(t => t.id));
    return this.allTags().filter(t => !assigned.has(t.id));
  });

  editForm = this.fb.group({
    first_name:    ['', Validators.required],
    last_name:     ['', Validators.required],
    maiden_name:   [''], gender: [''],
    birth_date:    [''], birth_place: [''],
    death_date:    [''], death_place: [''],
    is_living:     [true], occupation: [''],
    nationality:   [''], biography: [''],
    privacy_level: ['private'],
  });

  filiationForm = this.fb.group({
    person_id:      ['', Validators.required],
    filiation_type: ['biological'],
  });

  unionForm = this.fb.group({
    person_id_2:      ['', Validators.required],
    union_type:       ['mariage'],
    date_union:       [''],
    lieu_union:       [''],
    date_dissolution: [''],
    statut:           ['actif'],
  });

  eventForm = this.fb.group({
    event_type:  ['custom', Validators.required],
    date_start:  [''],
    date_end:    [''],
    place:       [''],
    description: [''],
  });

  ngOnInit() {
    if (!this.auth.currentUser()) this.auth.fetchCurrentUser().subscribe();
    const id = this.route.snapshot.paramMap.get('id')!;
    this.loadAll(id);
    this.personSvc.list(1, 200).subscribe({ next: r => this.allPersons.set(r.items) });
    this.tagSvc.list().subscribe({ next: r => this.allTags.set(r.items) });
    this.tagSvc.getPersonTags(id).subscribe({ next: tags => this.personTags.set(tags) });
  }

  private loadAll(id: string) {
    this.loading.set(true);
    forkJoin({
      person:   this.personSvc.get(id),
      parents:  this.filSvc.getParents(id),
      children: this.filSvc.getChildren(id),
      unions:   this.unionSvc.getByPerson(id),
      media:    this.mediaSvc.getByOwner('person', id),
      events:   this.eventSvc.getByPerson(id),
    }).subscribe({
      next: d => {
        this.person.set(d.person);
        this.parents.set(d.parents);
        this.children.set(d.children);
        this.unions.set(d.unions);
        this.media.set(d.media);
        this.events.set([...d.events].sort((a, b) => (a.date_start ?? '').localeCompare(b.date_start ?? '')));
        this.loading.set(false);
      },
      error: () => { this.error.set('Impossible de charger les données.'); this.loading.set(false); }
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  personName(id: string) {
    const p = this.personMap().get(id);
    return p ? `${p.first_name} ${p.last_name}` : '—';
  }
  partnerOf(u: Union) {
    const id = this.person()?.id;
    return this.personName(u.person_id_1 === id ? u.person_id_2 : u.person_id_1);
  }
  initials(p: Person) { return `${p.first_name[0] ?? ''}${p.last_name[0] ?? ''}`.toUpperCase(); }
  genderIcon(g?: string | null) { return g === 'male' ? '♂' : g === 'female' ? '♀' : '—'; }

  filTypeLabel(t: string) {
    const m: Record<string, string> = { biological: 'Biologique', adoptive: 'Adoptif(ve)', step: 'Beau-parent', guardian: 'Tuteur/Tutrice' };
    return m[t] ?? t;
  }
  unionTypeLabel(t: string) {
    const m: Record<string, string> = { mariage: 'Mariage', union_libre: 'Union libre', pacs: 'PACS', fiancailles: 'Fiançailles' };
    return m[t] ?? t;
  }
  eventTypeLabel(t: string) {
    const m: Record<string, string> = { birth: 'Naissance', death: 'Décès', baptism: 'Baptême', burial: 'Inhumation', education: 'Éducation', employment: 'Emploi', residence: 'Résidence', custom: 'Événement' };
    return m[t] ?? t;
  }
  eventIcon(t: string) {
    const m: Record<string, string> = { birth: '🐣', death: '✝️', baptism: '✨', burial: '⚱️', education: '🎓', employment: '💼', residence: '🏠', custom: '📅' };
    return m[t] ?? '📅';
  }
  private readonly API_BASE = 'http://localhost:8090';
  getMediaSrc(m: Media): string {
    const url = m.thumbnail_url || m.url;
    if (!url) return '';
    return url.startsWith('http') ? url : `${this.API_BASE}${url}`;
  }
  isImage(m: Media) {
    if (m.mime_type) return m.mime_type.startsWith('image/');
    return /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(m.url ?? '');
  }
  fileName(m: Media) { return m.filename ?? (m.url ?? m.id).split('/').pop()?.split('?')[0] ?? m.id; }
  availablePersons() { const id = this.person()?.id; return this.allPersons().filter(p => p.id !== id); }
  availablePartners() {
    const pid = this.person()?.id;
    const taken = new Set([
      ...this.unions().map(u => u.person_id_1 === pid ? u.person_id_2 : u.person_id_1),
    ]);
    if (this.unionEditTarget()) taken.delete(this.partnerOf(this.unionEditTarget()!));
    return this.allPersons().filter(p => p.id !== pid);
  }

  // ── Edit person ─────────────────────────────────────────────────────────────
  openEdit() {
    const p = this.person()!;
    this.editForm.patchValue({
      first_name: p.first_name, last_name: p.last_name,
      maiden_name: p.maiden_name ?? '', gender: p.gender ?? '',
      birth_date: p.birth_date ?? '', birth_place: p.birth_place ?? '',
      death_date: p.death_date ?? '', death_place: p.death_place ?? '',
      is_living: p.is_living, occupation: p.occupation ?? '',
      nationality: p.nationality ?? '', biography: p.biography ?? '',
      privacy_level: p.privacy_level,
    });
    this.editModal.set(true);
  }
  saveEdit() {
    if (this.editForm.invalid) { this.editForm.markAllAsTouched(); return; }
    this.saving.set(true);
    const v = this.editForm.getRawValue();
    const payload: PersonCreate = {
      first_name: v.first_name!, last_name: v.last_name!,
      maiden_name: v.maiden_name || undefined, gender: (v.gender as any) || undefined,
      birth_date: v.birth_date || undefined,   birth_place: v.birth_place || undefined,
      death_date: v.death_date || undefined,   death_place: v.death_place || undefined,
      is_living: !!v.is_living, occupation: v.occupation || undefined,
      nationality: v.nationality || undefined, biography: v.biography || undefined,
      privacy_level: (v.privacy_level as any) || 'private',
    };
    this.personSvc.update(this.person()!.id, payload).subscribe({
      next: saved => { this.person.set(saved); this.editModal.set(false); this.saving.set(false); this.flash('Profil mis à jour.'); },
      error: err  => { this.saving.set(false); this.error.set(err.error?.detail ?? 'Erreur.'); }
    });
  }

  // ── Filiation ────────────────────────────────────────────────────────────────
  openAddFiliation(role: 'parent' | 'child') {
    this.filiationRole.set(role);
    this.filiationForm.reset({ filiation_type: 'biological' });
    this.filiationModal.set(true);
  }
  saveFiliation() {
    const v = this.filiationForm.getRawValue();
    if (!v.person_id) return;
    this.saving.set(true);
    const pid = this.person()!.id;
    const isParent = this.filiationRole() === 'parent';
    this.filSvc.create({
      parent_id:      isParent ? v.person_id! : pid,
      child_id:       isParent ? pid : v.person_id!,
      filiation_type: (v.filiation_type as FiliationType) || 'biological',
    }).subscribe({
      next: f => {
        if (isParent) this.parents.update(l => [...l, f]);
        else          this.children.update(l => [...l, f]);
        this.filiationModal.set(false);
        this.saving.set(false);
        this.flash(isParent ? 'Parent ajouté.' : 'Enfant ajouté.');
      },
      error: err => { this.saving.set(false); this.error.set(err.error?.detail ?? 'Erreur.'); }
    });
  }

  // ── Union ────────────────────────────────────────────────────────────────────
  openAddUnion() {
    this.unionEditTarget.set(null);
    this.unionForm.reset({ union_type: 'mariage', statut: 'actif' });
    this.unionModal.set(true);
  }
  openEditUnion(u: Union) {
    this.unionEditTarget.set(u);
    const pid = this.person()!.id;
    this.unionForm.patchValue({
      person_id_2:      u.person_id_1 === pid ? u.person_id_2 : u.person_id_1,
      union_type:       u.union_type,
      date_union:       u.date_union       ?? '',
      lieu_union:       u.lieu_union       ?? '',
      date_dissolution: u.date_dissolution ?? '',
      statut:           u.statut,
    });
    this.unionModal.set(true);
  }
  saveUnion() {
    if (this.unionForm.invalid) return;
    this.saving.set(true);
    const v   = this.unionForm.getRawValue();
    const pid = this.person()!.id;
    const target = this.unionEditTarget();
    const obs: Observable<Union> = target
      ? this.unionSvc.update(target.id, {
          union_type:  v.union_type       as UnionType,
          date_union:  v.date_union       || undefined,
          lieu_union:  v.lieu_union       || undefined,
          date_dissolution: v.date_dissolution || undefined,
          statut:      v.statut           as UnionStatut,
        })
      : this.unionSvc.create({
          person_id_1: pid,
          person_id_2: v.person_id_2!,
          union_type:  v.union_type       as UnionType,
          date_union:  v.date_union       || undefined,
          lieu_union:  v.lieu_union       || undefined,
          date_dissolution: v.date_dissolution || undefined,
          statut:      v.statut           as UnionStatut,
        });
    obs.subscribe({
      next: saved => {
        this.unions.update(l => target ? l.map(x => x.id === saved.id ? saved : x) : [...l, saved]);
        this.unionModal.set(false);
        this.unionEditTarget.set(null);
        this.saving.set(false);
        this.flash(target ? 'Union modifiée.' : 'Union ajoutée.');
      },
      error: err => { this.saving.set(false); this.error.set(err.error?.detail ?? 'Erreur.'); }
    });
  }

  // ── Event ─────────────────────────────────────────────────────────────────────
  openAddEvent() {
    this.eventEditTarget.set(null);
    this.eventForm.reset({ event_type: 'custom' });
    this.eventModal.set(true);
  }
  openEditEvent(e: LifeEvent) {
    this.eventEditTarget.set(e);
    this.eventForm.patchValue({
      event_type: e.event_type, date_start: e.date_start ?? '',
      date_end: e.date_end ?? '', place: e.place ?? '', description: e.description ?? '',
    });
    this.eventModal.set(true);
  }
  saveEvent() {
    if (this.eventForm.invalid) return;
    this.saving.set(true);
    const v      = this.eventForm.getRawValue();
    const pid    = this.person()!.id;
    const target = this.eventEditTarget();
    const obs: Observable<LifeEvent> = target
      ? this.eventSvc.update(target.id, {
          event_type: v.event_type as EventType,
          date_start: v.date_start || undefined, date_end: v.date_end || undefined,
          place: v.place || undefined, description: v.description || undefined,
        })
      : this.eventSvc.create({
          person_id: pid, event_type: v.event_type as EventType,
          date_start: v.date_start || undefined, date_end: v.date_end || undefined,
          place: v.place || undefined, description: v.description || undefined,
        });
    obs.subscribe({
      next: saved => {
        const sorted = (l: LifeEvent[]) => [...l].sort((a, b) => (a.date_start ?? '').localeCompare(b.date_start ?? ''));
        this.events.update(l => sorted(target ? l.map(x => x.id === saved.id ? saved : x) : [...l, saved]));
        this.eventModal.set(false);
        this.eventEditTarget.set(null);
        this.saving.set(false);
        this.flash(target ? 'Événement modifié.' : 'Événement ajouté.');
      },
      error: err => { this.saving.set(false); this.error.set(err.error?.detail ?? 'Erreur.'); }
    });
  }

  // ── Generic delete ───────────────────────────────────────────────────────────
  openDelete(dtype: DelType, id: string, label: string) {
    this.deleteModal.set({ dtype, id, label });
  }
  confirmDelete() {
    const dm = this.deleteModal();
    if (!dm) return;
    this.saving.set(true);
    const delObs: Record<string, () => Observable<void>> = {
      'filiation-parent': () => this.filSvc.delete(dm.id),
      'filiation-child':  () => this.filSvc.delete(dm.id),
      'union':            () => this.unionSvc.delete(dm.id),
      'media':            () => this.mediaSvc.delete(dm.id),
      'event':            () => this.eventSvc.delete(dm.id),
    };
    delObs[dm.dtype]().subscribe({
      next: () => {
        this.removeItem(dm.dtype, dm.id);
        this.deleteModal.set(null);
        this.saving.set(false);
        this.flash('Supprimé avec succès.');
      },
      error: () => { this.saving.set(false); this.error.set('Erreur lors de la suppression.'); }
    });
  }
  private removeItem(dtype: DelType, id: string) {
    switch (dtype) {
      case 'filiation-parent': this.parents.update(l => l.filter(x => x.id !== id)); break;
      case 'filiation-child':  this.children.update(l => l.filter(x => x.id !== id)); break;
      case 'union':            this.unions.update(l => l.filter(x => x.id !== id));   break;
      case 'media':            this.media.update(l => l.filter(x => x.id !== id));    break;
      case 'event':            this.events.update(l => l.filter(x => x.id !== id));   break;
    }
  }

  // ── Media upload ─────────────────────────────────────────────────────────────
  triggerUpload() { this.uploadInputRef.nativeElement.click(); }
  onFileChange(ev: Event) {
    const f = (ev.target as HTMLInputElement).files?.[0];
    if (f) this.doUpload(f);
  }
  private doUpload(file: File) {
    const pid = this.person()!.id;
    this.uploading.set(true);
    this.uploadProgress.set(0);
    this.mediaSvc.upload(file, 'person', pid).subscribe({
      next: ev => {
        this.uploadProgress.set(ev.progress);
        if (ev.result) {
          this.media.update(l => [{ ...ev.result! } as Media, ...l]);
          this.uploading.set(false);
          this.flash('Photo ajoutée.');
          this.uploadInputRef.nativeElement.value = '';
        }
      },
      error: err => { this.uploading.set(false); this.error.set(err.error?.detail ?? "Erreur upload."); }
    });
  }

  // ── Tags ────────────────────────────────────────────────────────────────────
  openTagPicker()  { this.tagPickerOpen.set(true); this.newTagLabel.set(''); }
  closeTagPicker() { this.tagPickerOpen.set(false); }

  addTag(tag: Tag) {
    const pid = this.person()?.id;
    if (!pid) return;
    this.tagSvc.addTagToPerson(pid, tag.id).subscribe({
      next: () => {
        this.personTags.update(list => [...list, tag]);
        this.flash(`Tag "${tag.label}" ajouté.`);
      },
      error: () => this.error.set('Impossible d\'ajouter le tag.'),
    });
  }

  removeTag(tag: Tag) {
    const pid = this.person()?.id;
    if (!pid) return;
    this.tagSvc.removeTagFromPerson(pid, tag.id).subscribe({
      next: () => {
        this.personTags.update(list => list.filter(t => t.id !== tag.id));
        this.flash(`Tag "${tag.label}" retiré.`);
      },
      error: () => this.error.set('Impossible de retirer le tag.'),
    });
  }

  createAndAddTag() {
    const label = this.newTagLabel().trim();
    if (!label) return;
    this.savingTag.set(true);
    this.tagSvc.create({ label, color: this.newTagColor() }).subscribe({
      next: tag => {
        this.allTags.update(list => [...list, tag]);
        this.savingTag.set(false);
        this.newTagLabel.set('');
        this.addTag(tag);
      },
      error: err => {
        this.savingTag.set(false);
        this.error.set(err.error?.detail ?? 'Erreur lors de la création du tag.');
      },
    });
  }

  private flash(msg: string) {
    this.success.set(msg);
    setTimeout(() => this.success.set(null), 3000);
  }
}
