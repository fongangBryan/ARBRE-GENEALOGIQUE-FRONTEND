import { Component, inject, signal, OnInit, computed, ElementRef, ViewChild } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { AppShellComponent } from '../../shared/components/app-shell/app-shell';
import { MediaService } from '../../services/media.service';
import { PersonService } from '../../services/person.service';
import { UnionService } from '../../services/union.service';
import { Media } from '../../models/media.model';
import { Person } from '../../models/person.model';
import { Union } from '../../models/union.model';
import { AuthService } from '../../services/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-media',
  standalone: true,
  imports: [AppShellComponent, FormsModule],
  templateUrl: './media.html',
  styleUrl: './media.css',
})
export class MediaComponent implements OnInit {
  @ViewChild('fileInput') fileInputRef!: ElementRef<HTMLInputElement>;

  private mediaSvc  = inject(MediaService);
  private pSvc      = inject(PersonService);
  private unionSvc  = inject(UnionService);
  private sanitizer = inject(DomSanitizer);
  readonly auth     = inject(AuthService);

  ownerType       = signal<'person' | 'union'>('person');
  persons         = signal<Person[]>([]);
  selectedPid     = signal('');
  availableUnions = signal<Union[]>([]);
  ownerId         = signal('');
  media           = signal<Media[]>([]);
  loading         = signal(false);
  uploading       = signal(false);
  progress        = signal(0);
  dragOver        = signal(false);
  error           = signal<string | null>(null);
  success         = signal<string | null>(null);
  deleteTarget    = signal<Media | null>(null);
  deleting        = signal(false);
  previewTarget   = signal<Media | null>(null);

  readonly isEditor = computed(() => {
    const role = this.auth.currentUser()?.role;
    return role === 'editor' || role === 'admin';
  });

  readonly personMap = computed(() => {
    const m = new Map<string, Person>();
    this.persons().forEach(p => m.set(p.id, p));
    return m;
  });

  ngOnInit() {
    if (!this.auth.currentUser()) this.auth.fetchCurrentUser().subscribe();
    this.pSvc.list(1, 200).subscribe({ next: r => this.persons.set(r.items) });
  }

  changeOwnerType(t: 'person' | 'union') {
    this.ownerType.set(t);
    this.selectedPid.set('');
    this.ownerId.set('');
    this.availableUnions.set([]);
    this.media.set([]);
  }

  onPersonSelect(pid: string) {
    this.selectedPid.set(pid);
    this.ownerId.set('');
    this.availableUnions.set([]);
    this.media.set([]);
    if (!pid) return;
    if (this.ownerType() === 'person') {
      this.ownerId.set(pid);
      this.fetchMedia(pid, 'person');
    } else {
      this.unionSvc.getByPerson(pid).subscribe({ next: list => this.availableUnions.set(list) });
    }
  }

  onUnionSelect(uid: string) {
    this.ownerId.set(uid);
    this.media.set([]);
    if (uid) this.fetchMedia(uid, 'union');
  }

  private fetchMedia(id: string, type: string) {
    this.loading.set(true);
    this.mediaSvc.getByOwner(type, id).subscribe({
      next: list => { this.media.set(list); this.loading.set(false); },
      error: () => { this.error.set('Impossible de charger les médias.'); this.loading.set(false); }
    });
  }

  unionLabel(u: Union): string {
    const p1 = this.personMap().get(u.person_id_1);
    const p2 = this.personMap().get(u.person_id_2);
    const n1 = p1 ? `${p1.first_name} ${p1.last_name}` : '?';
    const n2 = p2 ? `${p2.first_name} ${p2.last_name}` : '?';
    return `${n1} & ${n2}` + (u.date_union ? ` (${u.date_union})` : '');
  }

  onDragOver(ev: DragEvent)  { ev.preventDefault(); this.dragOver.set(true); }
  onDragLeave()               { this.dragOver.set(false); }
  onDrop(ev: DragEvent) {
    ev.preventDefault();
    this.dragOver.set(false);
    const f = ev.dataTransfer?.files?.[0];
    if (f) this.doUpload(f);
  }
  onFileChange(ev: Event) {
    const f = (ev.target as HTMLInputElement).files?.[0];
    if (f) this.doUpload(f);
  }
  triggerInput() { this.fileInputRef.nativeElement.click(); }

  doUpload(file: File) {
    const id = this.ownerId();
    const ot = this.ownerType();
    if (!id) { this.error.set('Sélectionnez un propriétaire avant d\'uploader.'); return; }
    this.uploading.set(true);
    this.progress.set(0);
    this.mediaSvc.upload(file, ot, id).subscribe({
      next: ev => {
        this.progress.set(ev.progress);
        if (ev.result) {
          const m: Media = { ...ev.result };
          this.media.update(list => [m, ...list]);
          this.uploading.set(false);
          this.flash('Fichier ajouté avec succès.');
          this.fileInputRef.nativeElement.value = '';
        }
      },
      error: err => {
        this.uploading.set(false);
        this.error.set(err.error?.detail ?? "Erreur lors de l'upload.");
      }
    });
  }

  openPreview(m: Media)  { this.previewTarget.set(m); }
  closePreview()         { this.previewTarget.set(null); }

  isPdf(m: Media): boolean {
    return (m.mime_type?.includes('pdf') ?? false) || /\.pdf$/i.test(m.url ?? '');
  }

  pdfSrc(m: Media): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(this.getMediaSrc(m));
  }

  openDelete(m: Media)  { this.deleteTarget.set(m); }
  closeDelete()          { this.deleteTarget.set(null); }

  confirmDelete() {
    const m = this.deleteTarget();
    if (!m) return;
    this.deleting.set(true);
    this.mediaSvc.delete(m.id).subscribe({
      next: () => {
        this.media.update(list => list.filter(x => x.id !== m.id));
        this.deleteTarget.set(null);
        this.deleting.set(false);
        this.flash('Fichier supprimé.');
      },
      error: () => { this.deleting.set(false); this.error.set('Erreur lors de la suppression.'); }
    });
  }

  private readonly API_BASE = environment.apiBase;

  getMediaSrc(m: Media): string {
    const url = m.thumbnail_url || m.url;
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${this.API_BASE}${url}`;
  }

  isImage(m: Media): boolean {
    if (m.mime_type) return m.mime_type.startsWith('image/');
    return /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(m.url ?? '');
  }

  fileExt(m: Media): string {
    const mt = m.mime_type ?? '';
    if (mt.includes('pdf')) return 'PDF';
    if (mt.includes('video')) return 'VID';
    if (mt.includes('audio')) return 'SON';
    const name = m.filename ?? m.url ?? '';
    return (name.split('.').pop() ?? 'FIC').toUpperCase().slice(0, 4);
  }

  fileName(m: Media): string {
    if (m.filename) return m.filename;
    return (m.url ?? m.id).split('/').pop()?.split('?')[0] ?? m.id;
  }

  private flash(msg: string) {
    this.success.set(msg);
    setTimeout(() => this.success.set(null), 3000);
  }
}
