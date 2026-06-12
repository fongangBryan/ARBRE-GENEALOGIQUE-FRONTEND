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

import { PersonsComponent } from './persons';
import { PersonService } from '../../services/person.service';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';
import { Person, PersonListResponse } from '../../models/person.model';

// ── Helpers ────────────────────────────────────────────────────────────────────

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
    id: 'person-1',
    first_name: 'Jean',
    last_name: 'Dupont',
    is_living: true,
    privacy_level: 'private',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function makePersonList(persons: Person[] = [makePerson()]): PersonListResponse {
  return { items: persons, total: persons.length, page: 1, limit: 20, pages: 1 };
}

// ── Suite ──────────────────────────────────────────────────────────────────────

describe('PersonsComponent', () => {
  let component: PersonsComponent;
  let fixture: ComponentFixture<PersonsComponent>;
  let currentUserSignal: WritableSignal<User | null>;
  let personSpy: jasmine.SpyObj<PersonService>;

  beforeEach(async () => {
    currentUserSignal = signal<User | null>(null);

    personSpy = jasmine.createSpyObj<PersonService>('PersonService', [
      'list', 'create', 'update', 'delete',
    ]);
    personSpy.list.and.returnValue(of(makePersonList()));

    await TestBed.configureTestingModule({
      imports: [PersonsComponent, FormsModule, ReactiveFormsModule],
      providers: [
        {
          provide: AuthService,
          useValue: {
            currentUser: currentUserSignal,
            fetchCurrentUser: jasmine.createSpy().and.returnValue(of(makeUser('editor'))),
          },
        },
        { provide: PersonService, useValue: personSpy },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: { get: () => null } } },
        },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(PersonsComponent);
    component = fixture.componentInstance;
  });

  // ── isEditor / isAdmin ───────────────────────────────────────────────────────

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

  describe('isAdmin()', () => {
    it('retourne true pour le rôle admin', () => {
      currentUserSignal.set(makeUser('admin'));
      expect(component.isAdmin()).toBeTrue();
    });

    it('retourne false pour le rôle editor', () => {
      currentUserSignal.set(makeUser('editor'));
      expect(component.isAdmin()).toBeFalse();
    });

    it('retourne false pour le rôle reader', () => {
      currentUserSignal.set(makeUser('reader'));
      expect(component.isAdmin()).toBeFalse();
    });
  });

  // ── Visibilité du bouton Supprimer ───────────────────────────────────────────

  describe('Bouton Supprimer — visibilité selon le rôle', () => {
    beforeEach(() => {
      personSpy.list.and.returnValue(of(makePersonList([makePerson()])));
    });

    it('P — ADMIN : bouton supprimer visible', fakeAsync(() => {
      currentUserSignal.set(makeUser('admin'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-del');
      expect(btn).not.toBeNull();
    }));

    it('P — EDITOR : bouton supprimer absent', fakeAsync(() => {
      currentUserSignal.set(makeUser('editor'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-del');
      expect(btn).toBeNull();
    }));

    it('P — READER : bouton supprimer absent', fakeAsync(() => {
      currentUserSignal.set(makeUser('reader'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-del');
      expect(btn).toBeNull();
    }));

    it('P — ADMIN : bouton modifier aussi visible', fakeAsync(() => {
      currentUserSignal.set(makeUser('admin'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-edit');
      expect(btn).not.toBeNull();
    }));

    it('P — EDITOR : bouton modifier visible', fakeAsync(() => {
      currentUserSignal.set(makeUser('editor'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-edit');
      expect(btn).not.toBeNull();
    }));

    it('P — READER : bouton modifier absent', fakeAsync(() => {
      currentUserSignal.set(makeUser('reader'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-edit');
      expect(btn).toBeNull();
    }));
  });

  // ── Visibilité du bouton Ajouter ─────────────────────────────────────────────

  describe('Bouton Ajouter un membre', () => {
    it('visible pour EDITOR', fakeAsync(() => {
      currentUserSignal.set(makeUser('editor'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-add');
      expect(btn).not.toBeNull();
    }));

    it('visible pour ADMIN', fakeAsync(() => {
      currentUserSignal.set(makeUser('admin'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-add');
      expect(btn).not.toBeNull();
    }));

    it('absent pour READER', fakeAsync(() => {
      currentUserSignal.set(makeUser('reader'));
      personSpy.list.and.returnValue(of(makePersonList()));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.btn-add');
      expect(btn).toBeNull();
    }));
  });

  // ── Modal de suppression ─────────────────────────────────────────────────────

  describe('Modal de suppression', () => {
    const person = makePerson();

    it('openDelete() positionne deleteTarget sur la personne', () => {
      component.openDelete(person);
      expect(component.deleteTarget()).toEqual(person);
    });

    it('closeDelete() réinitialise deleteTarget', () => {
      component.openDelete(person);
      component.closeDelete();
      expect(component.deleteTarget()).toBeNull();
    });

    it('confirmDelete() appelle personService.delete avec le bon ID', () => {
      personSpy.delete.and.returnValue(of(undefined));
      personSpy.list.and.returnValue(of(makePersonList([person])));
      fixture.detectChanges();

      component.openDelete(person);
      component.confirmDelete();

      expect(personSpy.delete).toHaveBeenCalledWith(person.id);
    });

    it('confirmDelete() supprime la personne de la liste locale', fakeAsync(() => {
      personSpy.delete.and.returnValue(of(undefined));
      personSpy.list.and.returnValue(of(makePersonList([person])));
      fixture.detectChanges();
      tick();

      component.openDelete(person);
      component.confirmDelete();
      tick();

      expect(component.persons().find(p => p.id === person.id)).toBeUndefined();
    }));

    it('confirmDelete() décrémente le total', fakeAsync(() => {
      personSpy.delete.and.returnValue(of(undefined));
      personSpy.list.and.returnValue(of(makePersonList([person])));
      fixture.detectChanges();
      tick();

      const totalBefore = component.total();
      component.openDelete(person);
      component.confirmDelete();
      tick();

      expect(component.total()).toBe(totalBefore - 1);
    }));

    it('confirmDelete() ferme le modal après succès', fakeAsync(() => {
      personSpy.delete.and.returnValue(of(undefined));
      fixture.detectChanges();

      component.openDelete(person);
      component.confirmDelete();
      tick();

      expect(component.deleteTarget()).toBeNull();
    }));

    it('confirmDelete() affiche une erreur en cas d\'échec API', fakeAsync(() => {
      personSpy.delete.and.returnValue(throwError(() => new Error('Server error')));
      fixture.detectChanges();

      component.openDelete(person);
      component.confirmDelete();
      tick();

      expect(component.error()).toBeTruthy();
    }));
  });

  // ── ngOnInit ──────────────────────────────────────────────────────────────────

  describe('ngOnInit()', () => {
    it('appelle personService.list au démarrage', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(personSpy.list).toHaveBeenCalledWith(1, 20, '');
    }));

    it('remplit persons() avec les données reçues', fakeAsync(() => {
      const persons = [makePerson({ id: 'p1' }), makePerson({ id: 'p2' })];
      personSpy.list.and.returnValue(of(makePersonList(persons)));

      fixture.detectChanges();
      tick();

      expect(component.persons().length).toBe(2);
    }));

    it('positionne loading à false après chargement', fakeAsync(() => {
      fixture.detectChanges();
      tick();
      expect(component.loading()).toBeFalse();
    }));

    it('positionne error en cas d\'échec de chargement', fakeAsync(() => {
      personSpy.list.and.returnValue(throwError(() => new Error('Network error')));
      fixture.detectChanges();
      tick();

      expect(component.error()).toBeTruthy();
      expect(component.loading()).toBeFalse();
    }));
  });

  // ── Modales Create/Edit ───────────────────────────────────────────────────────

  describe('openCreate()', () => {
    it('ouvre le modal en mode create', () => {
      component.openCreate();
      expect(component.modalMode()).toBe('create');
    });

    it('réinitialise le formulaire', () => {
      component.form.patchValue({ first_name: 'Test' });
      component.openCreate();
      expect(component.form.value.first_name).toBeFalsy();
    });
  });

  describe('openEdit()', () => {
    it('ouvre le modal en mode edit avec les données de la personne', () => {
      const person = makePerson({ first_name: 'Alice', last_name: 'Bob' });
      component.openEdit(person);

      expect(component.modalMode()).toBe('edit');
      expect(component.editTarget()).toEqual(person);
      expect(component.form.value.first_name).toBe('Alice');
    });
  });

  describe('closeModal()', () => {
    it('ferme le modal', () => {
      component.openCreate();
      component.closeModal();
      expect(component.modalMode()).toBeNull();
    });
  });

  // ── Pagination ────────────────────────────────────────────────────────────────

  describe('Pagination', () => {
    beforeEach(() => {
      component.totalPages.set(3);
      component.page.set(2);
    });

    it('prevPage() décrémente la page', () => {
      component.prevPage();
      expect(personSpy.list).toHaveBeenCalledWith(1, jasmine.any(Number), jasmine.any(String));
    });

    it('nextPage() incrémente la page', () => {
      component.nextPage();
      expect(personSpy.list).toHaveBeenCalledWith(3, jasmine.any(Number), jasmine.any(String));
    });

    it('prevPage() ne descend pas en dessous de 1', () => {
      component.page.set(1);
      component.prevPage();
      expect(personSpy.list).not.toHaveBeenCalledWith(0, jasmine.any(Number), jasmine.any(String));
    });

    it('nextPage() ne dépasse pas totalPages', () => {
      component.page.set(3);
      component.nextPage();
      expect(personSpy.list).not.toHaveBeenCalledWith(4, jasmine.any(Number), jasmine.any(String));
    });
  });

  // ── Helpers visuels ───────────────────────────────────────────────────────────

  describe('initials()', () => {
    it('retourne les initiales en majuscules', () => {
      const p = makePerson({ first_name: 'jean', last_name: 'dupont' });
      expect(component.initials(p)).toBe('JD');
    });
  });

  describe('genderIcon()', () => {
    it('retourne ♂ pour male', () => expect(component.genderIcon('male')).toBe('♂'));
    it('retourne ♀ pour female', () => expect(component.genderIcon('female')).toBe('♀'));
    it('retourne — pour autre', () => expect(component.genderIcon('other')).toBe('—'));
    it('retourne — pour null', () => expect(component.genderIcon(null)).toBe('—'));
  });
});
