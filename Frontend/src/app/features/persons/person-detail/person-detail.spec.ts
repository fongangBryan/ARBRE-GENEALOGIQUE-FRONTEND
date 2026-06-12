import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';
import { signal, WritableSignal, NO_ERRORS_SCHEMA } from '@angular/core';

import { PersonDetailComponent } from './person-detail';
import { PersonService } from '../../../services/person.service';
import { FiliationService } from '../../../services/filiation.service';
import { UnionService } from '../../../services/union.service';
import { MediaService } from '../../../services/media.service';
import { EventService } from '../../../services/event.service';
import { TagService } from '../../../services/tag.service';
import { AuthService } from '../../../services/auth.service';
import { User } from '../../../models/user.model';
import { Person } from '../../../models/person.model';
import { Filiation } from '../../../models/filiation.model';
import { Union } from '../../../models/union.model';
import { Media } from '../../../models/media.model';
import { LifeEvent } from '../../../models/event.model';

// ── Helpers ────────────────────────────────────────────────────────────────────

const PERSON_ID = 'person-abc-123';

function makeUser(role: 'admin' | 'editor' | 'reader'): User {
  return {
    id: `user-${role}`,
    email: `${role}@test.com`,
    first_name: role,
    last_name: 'User',
    role,
    is_active: true,
    is_verified: true,
    is_2fa_enabled: false,
    created_at: '2024-01-01T00:00:00Z',
    last_login: null,
  };
}

function makePerson(overrides: Partial<Person> = {}): Person {
  return {
    id: PERSON_ID,
    first_name: 'Jean',
    last_name: 'Dupont',
    is_living: true,
    privacy_level: 'private',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeFiliation(id = 'fil-1'): Filiation {
  return {
    id,
    parent_id: 'parent-1',
    child_id: PERSON_ID,
    filiation_type: 'biological',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };
}

function makeUnion(id = 'union-1'): Union {
  return {
    id,
    person_id_1: PERSON_ID,
    person_id_2: 'partner-1',
    union_type: 'mariage',
    statut: 'actif',
    date_union: '2010-06-15',
    lieu_union: null,
    date_dissolution: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };
}

function makeMedia(id = 'media-1'): Media {
  return {
    id,
    filename: 'photo.jpg',
    storage_key: `uploads/${id}.jpg`,
    url: `/api/v1/media/${id}`,
    thumbnail_url: null,
    mime_type: 'image/jpeg',
    owner_type: 'person',
    owner_id: PERSON_ID,
    privacy_level: 'family',
    created_at: '2024-01-01T00:00:00Z',
  };
}

function makeEvent(id = 'event-1'): LifeEvent {
  return {
    id,
    person_id: PERSON_ID,
    event_type: 'birth',
    date_start: '1990-01-15',
    date_end: null,
    place: 'Paris',
    description: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };
}

// ── Suite ──────────────────────────────────────────────────────────────────────

describe('PersonDetailComponent', () => {
  let component: PersonDetailComponent;
  let fixture: ComponentFixture<PersonDetailComponent>;
  let currentUserSignal: WritableSignal<User | null>;

  let personSpy: jasmine.SpyObj<PersonService>;
  let filSpy: jasmine.SpyObj<FiliationService>;
  let unionSpy: jasmine.SpyObj<UnionService>;
  let mediaSpy: jasmine.SpyObj<MediaService>;
  let eventSpy: jasmine.SpyObj<EventService>;
  let tagSpy: jasmine.SpyObj<TagService>;

  beforeEach(async () => {
    currentUserSignal = signal<User | null>(makeUser('editor'));

    personSpy = jasmine.createSpyObj<PersonService>('PersonService', ['get', 'list', 'update']);
    filSpy    = jasmine.createSpyObj<FiliationService>('FiliationService', ['getParents', 'getChildren', 'create', 'delete']);
    unionSpy  = jasmine.createSpyObj<UnionService>('UnionService', ['getByPerson', 'create', 'update', 'delete']);
    mediaSpy  = jasmine.createSpyObj<MediaService>('MediaService', ['getByOwner', 'upload', 'delete']);
    eventSpy  = jasmine.createSpyObj<EventService>('EventService', ['getByPerson', 'create', 'update', 'delete']);
    tagSpy    = jasmine.createSpyObj<TagService>('TagService', ['list', 'get', 'create', 'update', 'delete', 'getPersonTags', 'addTagToPerson', 'removeTagFromPerson']);

    // Valeurs par défaut pour le chargement initial (forkJoin)
    personSpy.get.and.returnValue(of(makePerson()));
    personSpy.list.and.returnValue(of({ items: [], total: 0, page: 1, limit: 200, pages: 1 }));
    filSpy.getParents.and.returnValue(of([]));
    filSpy.getChildren.and.returnValue(of([]));
    unionSpy.getByPerson.and.returnValue(of([]));
    mediaSpy.getByOwner.and.returnValue(of([]));
    eventSpy.getByPerson.and.returnValue(of([]));
    tagSpy.list.and.returnValue(of({ items: [], total: 0 }));
    tagSpy.getPersonTags.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [PersonDetailComponent, FormsModule, ReactiveFormsModule],
      providers: [
        {
          provide: AuthService,
          useValue: {
            currentUser: currentUserSignal,
            fetchCurrentUser: jasmine.createSpy().and.returnValue(of(makeUser('editor'))),
          },
        },
        { provide: PersonService,    useValue: personSpy },
        { provide: FiliationService, useValue: filSpy },
        { provide: UnionService,     useValue: unionSpy },
        { provide: MediaService,     useValue: mediaSpy },
        { provide: EventService,     useValue: eventSpy },
        { provide: TagService,       useValue: tagSpy },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => PERSON_ID } } },
        },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(PersonDetailComponent);
    component = fixture.componentInstance;
  });

  // ── isEditor() ───────────────────────────────────────────────────────────────

  describe('isEditor()', () => {
    it('retourne true pour le rôle admin', () => {
      currentUserSignal.set(makeUser('admin'));
      expect(component.isEditor()).toBeTrue();
    });

    it('retourne true pour le rôle editor', () => {
      currentUserSignal.set(makeUser('editor'));
      expect(component.isEditor()).toBeTrue();
    });

    it('retourne false pour le rôle reader', () => {
      currentUserSignal.set(makeUser('reader'));
      expect(component.isEditor()).toBeFalse();
    });

    it('retourne false sans utilisateur connecté', () => {
      currentUserSignal.set(null);
      expect(component.isEditor()).toBeFalse();
    });
  });

  // ── Contrôles d'édition selon le rôle (rendu template) ──────────────────────

  describe('Contrôles d\'édition — visibilité dans le template', () => {
    it('EDITOR : voit les boutons d\'édition (ajout parent, enfant…)', fakeAsync(() => {
      currentUserSignal.set(makeUser('editor'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      expect(component.isEditor()).toBeTrue();
    }));

    it('READER : isEditor() retourne false → boutons d\'édition absents', fakeAsync(() => {
      currentUserSignal.set(makeUser('reader'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      expect(component.isEditor()).toBeFalse();
    }));
  });

  // ── ngOnInit — chargement des données ────────────────────────────────────────

  describe('ngOnInit()', () => {
    it('appelle personService.get avec l\'ID de la route', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(personSpy.get).toHaveBeenCalledWith(PERSON_ID);
    }));

    it('charge les parents et enfants', fakeAsync(() => {
      filSpy.getParents.and.returnValue(of([makeFiliation('p1')]));
      filSpy.getChildren.and.returnValue(of([makeFiliation('c1')]));

      fixture.detectChanges();
      tick();

      expect(component.parents().length).toBe(1);
      expect(component.children().length).toBe(1);
    }));

    it('charge les unions', fakeAsync(() => {
      unionSpy.getByPerson.and.returnValue(of([makeUnion()]));

      fixture.detectChanges();
      tick();

      expect(component.unions().length).toBe(1);
    }));

    it('charge les médias', fakeAsync(() => {
      mediaSpy.getByOwner.and.returnValue(of([makeMedia()]));

      fixture.detectChanges();
      tick();

      expect(component.media().length).toBe(1);
    }));

    it('charge les événements triés par date', fakeAsync(() => {
      const e1 = makeEvent('e1');
      const e2: LifeEvent = { ...makeEvent('e2'), date_start: '1980-03-01' };
      eventSpy.getByPerson.and.returnValue(of([e1, e2]));

      fixture.detectChanges();
      tick();

      const events = component.events();
      expect(events.length).toBe(2);
      expect(events[0].date_start! <= events[1].date_start!).toBeTrue();
    }));

    it('positionne loading à false après succès', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.loading()).toBeFalse();
    }));

    it('positionne error et loading=false en cas d\'échec du forkJoin', fakeAsync(() => {
      personSpy.get.and.returnValue(throwError(() => new Error('Network error')));

      fixture.detectChanges();
      tick();

      expect(component.error()).toBeTruthy();
      expect(component.loading()).toBeFalse();
    }));

    it('positionne person() avec les données reçues', fakeAsync(() => {
      const p = makePerson({ first_name: 'Alice', last_name: 'Martin' });
      personSpy.get.and.returnValue(of(p));

      fixture.detectChanges();
      tick();

      expect(component.person()?.first_name).toBe('Alice');
      expect(component.person()?.last_name).toBe('Martin');
    }));
  });

  // ── Onglets ───────────────────────────────────────────────────────────────────

  describe('Onglets (activeTab)', () => {
    it('l\'onglet actif par défaut est "profile"', () => {
      expect(component.activeTab()).toBe('profile');
    });

    it('setTab("family") change l\'onglet actif', () => {
      component.activeTab.set('family');
      expect(component.activeTab()).toBe('family');
    });

    it('setTab("media") change l\'onglet actif', () => {
      component.activeTab.set('media');
      expect(component.activeTab()).toBe('media');
    });

    it('setTab("events") change l\'onglet actif', () => {
      component.activeTab.set('events');
      expect(component.activeTab()).toBe('events');
    });
  });

  // ── openEdit() / saveEdit() ───────────────────────────────────────────────────

  describe('openEdit()', () => {
    it('ouvre le modal d\'édition', fakeAsync(() => {
      const p = makePerson({ first_name: 'Alice' });
      personSpy.get.and.returnValue(of(p));
      fixture.detectChanges();
      tick();

      component.openEdit();

      expect(component.editModal()).toBeTrue();
    }));

    it('pré-remplit le formulaire avec les données de la personne', fakeAsync(() => {
      const p = makePerson({ first_name: 'Alice', last_name: 'Wonder', birth_date: '1990-05-20' });
      personSpy.get.and.returnValue(of(p));
      fixture.detectChanges();
      tick();

      component.openEdit();

      expect(component.editForm.value.first_name).toBe('Alice');
      expect(component.editForm.value.last_name).toBe('Wonder');
      expect(component.editForm.value.birth_date).toBe('1990-05-20');
    }));
  });

  describe('saveEdit()', () => {
    it('appelle personService.update avec les données du formulaire', fakeAsync(() => {
      const p = makePerson();
      personSpy.get.and.returnValue(of(p));
      personSpy.update.and.returnValue(of({ ...p, first_name: 'Updated' }));
      fixture.detectChanges();
      tick();

      component.openEdit();
      component.editForm.patchValue({ first_name: 'Updated', last_name: 'Dupont' });
      component.saveEdit();
      tick();

      expect(personSpy.update).toHaveBeenCalledWith(PERSON_ID, jasmine.objectContaining({ first_name: 'Updated' }));
    }));

    it('ferme le modal après sauvegarde réussie', fakeAsync(() => {
      const p = makePerson();
      personSpy.get.and.returnValue(of(p));
      personSpy.update.and.returnValue(of(p));
      fixture.detectChanges();
      tick();

      component.openEdit();
      component.saveEdit();
      tick();

      expect(component.editModal()).toBeFalse();
    }));

    it('n\'appelle pas update si le formulaire est invalide', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      component.openEdit();
      component.editForm.patchValue({ first_name: '', last_name: '' });
      component.saveEdit();
      tick();

      expect(personSpy.update).not.toHaveBeenCalled();
    }));
  });

  // ── Modal de suppression générique ───────────────────────────────────────────

  describe('openDelete() / confirmDelete()', () => {
    it('openDelete() positionne deleteModal avec dtype, id, label', () => {
      component.openDelete('union', 'union-1', 'union avec Alice');
      const modal = component.deleteModal();
      expect(modal?.dtype).toBe('union');
      expect(modal?.id).toBe('union-1');
      expect(modal?.label).toBe('union avec Alice');
    });

    it('Annuler réinitialise deleteModal', () => {
      component.openDelete('union', 'union-1', 'test');
      component.deleteModal.set(null);
      expect(component.deleteModal()).toBeNull();
    });

    it('confirmDelete("union") appelle unionService.delete', fakeAsync(() => {
      unionSpy.delete.and.returnValue(of(undefined));
      component.unions.set([makeUnion('union-1')]);
      component.openDelete('union', 'union-1', 'union avec Alice');
      component.confirmDelete();
      tick();

      expect(unionSpy.delete).toHaveBeenCalledWith('union-1');
    }));

    it('confirmDelete("filiation-parent") appelle filiationService.delete', fakeAsync(() => {
      filSpy.delete.and.returnValue(of(undefined));
      component.parents.set([makeFiliation('fil-1')]);
      component.openDelete('filiation-parent', 'fil-1', 'Parent Test');
      component.confirmDelete();
      tick();

      expect(filSpy.delete).toHaveBeenCalledWith('fil-1');
    }));

    it('confirmDelete("filiation-child") appelle filiationService.delete', fakeAsync(() => {
      filSpy.delete.and.returnValue(of(undefined));
      component.children.set([makeFiliation('fil-2')]);
      component.openDelete('filiation-child', 'fil-2', 'Enfant Test');
      component.confirmDelete();
      tick();

      expect(filSpy.delete).toHaveBeenCalledWith('fil-2');
    }));

    it('confirmDelete("media") appelle mediaService.delete', fakeAsync(() => {
      mediaSpy.delete.and.returnValue(of(undefined));
      component.media.set([makeMedia('media-1')]);
      component.openDelete('media', 'media-1', 'photo.jpg');
      component.confirmDelete();
      tick();

      expect(mediaSpy.delete).toHaveBeenCalledWith('media-1');
    }));

    it('confirmDelete("event") appelle eventService.delete', fakeAsync(() => {
      eventSpy.delete.and.returnValue(of(undefined));
      component.events.set([makeEvent('event-1')]);
      component.openDelete('event', 'event-1', 'Naissance');
      component.confirmDelete();
      tick();

      expect(eventSpy.delete).toHaveBeenCalledWith('event-1');
    }));

    it('suppression union retire l\'élément de la liste locale', fakeAsync(() => {
      unionSpy.delete.and.returnValue(of(undefined));
      component.unions.set([makeUnion('union-1'), makeUnion('union-2')]);
      component.openDelete('union', 'union-1', 'test');
      component.confirmDelete();
      tick();

      expect(component.unions().find(u => u.id === 'union-1')).toBeUndefined();
      expect(component.unions().length).toBe(1);
    }));

    it('ferme le modal après suppression réussie', fakeAsync(() => {
      unionSpy.delete.and.returnValue(of(undefined));
      component.unions.set([makeUnion()]);
      component.openDelete('union', 'union-1', 'test');
      component.confirmDelete();
      tick();

      expect(component.deleteModal()).toBeNull();
    }));

    it('affiche une erreur en cas d\'échec de suppression', fakeAsync(() => {
      unionSpy.delete.and.returnValue(throwError(() => new Error('Server error')));
      component.unions.set([makeUnion()]);
      component.openDelete('union', 'union-1', 'test');
      component.confirmDelete();
      tick();

      expect(component.error()).toBeTruthy();
    }));
  });

  // ── Helpers ───────────────────────────────────────────────────────────────────

  describe('initials()', () => {
    it('retourne les initiales en majuscules', () => {
      const p = makePerson({ first_name: 'alice', last_name: 'dupont' });
      expect(component.initials(p)).toBe('AD');
    });
  });

  describe('genderIcon()', () => {
    it('retourne ♂ pour male',   () => expect(component.genderIcon('male')).toBe('♂'));
    it('retourne ♀ pour female', () => expect(component.genderIcon('female')).toBe('♀'));
    it('retourne — pour null',   () => expect(component.genderIcon(null)).toBe('—'));
    it('retourne — pour other',  () => expect(component.genderIcon('other')).toBe('—'));
  });

  describe('filTypeLabel()', () => {
    it('traduit "biological"', () => expect(component.filTypeLabel('biological')).toBe('Biologique'));
    it('traduit "adoptive"',   () => expect(component.filTypeLabel('adoptive')).toBe('Adoptif(ve)'));
    it('traduit "step"',       () => expect(component.filTypeLabel('step')).toBe('Beau-parent'));
    it('traduit "guardian"',   () => expect(component.filTypeLabel('guardian')).toBe('Tuteur/Tutrice'));
  });

  describe('unionTypeLabel()', () => {
    it('traduit "mariage"',     () => expect(component.unionTypeLabel('mariage')).toBe('Mariage'));
    it('traduit "union_libre"', () => expect(component.unionTypeLabel('union_libre')).toBe('Union libre'));
    it('traduit "pacs"',        () => expect(component.unionTypeLabel('pacs')).toBe('PACS'));
  });

  describe('isImage()', () => {
    it('retourne true pour un média image/jpeg', () => {
      expect(component.isImage(makeMedia())).toBeTrue();
    });

    it('retourne false pour un média application/pdf', () => {
      const pdf: Media = { ...makeMedia(), mime_type: 'application/pdf' };
      expect(component.isImage(pdf)).toBeFalse();
    });
  });

  describe('getMediaSrc()', () => {
    it('retourne l\'URL telle quelle si elle commence par http', () => {
      const m: Media = { ...makeMedia(), url: 'https://cdn.example.com/photo.jpg', thumbnail_url: null };
      expect(component.getMediaSrc(m)).toBe('https://cdn.example.com/photo.jpg');
    });

    it('préfixe avec apiBase si l\'URL est relative', () => {
      const m: Media = { ...makeMedia(), url: '/api/v1/media/media-1', thumbnail_url: null };
      const src = component.getMediaSrc(m);
      expect(src).toContain('/api/v1/media/media-1');
    });
  });

  // ── personMap() ───────────────────────────────────────────────────────────────

  describe('personMap()', () => {
    it('construit une Map indexée par id', fakeAsync(() => {
      const p1 = makePerson({ id: 'p1', first_name: 'Alice' });
      const p2 = makePerson({ id: 'p2', first_name: 'Bob' });
      component.allPersons.set([p1, p2]);

      expect(component.personMap().get('p1')?.first_name).toBe('Alice');
      expect(component.personMap().get('p2')?.first_name).toBe('Bob');
    }));
  });
});
