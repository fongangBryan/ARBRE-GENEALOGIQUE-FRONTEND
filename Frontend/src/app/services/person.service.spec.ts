import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { PersonService } from './person.service';
import { Person, PersonCreate, PersonListResponse } from '../models/person.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

// ── Données de test ────────────────────────────────────────────────────────────

const MOCK_PERSON: Person = {
  id: 'person-1',
  first_name: 'Jean',
  last_name: 'Dupont',
  gender: 'male',
  birth_date: '1990-01-15',
  birth_place: 'Paris',
  is_living: true,
  privacy_level: 'private',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_LIST: PersonListResponse = {
  items: [MOCK_PERSON],
  total: 1,
  page: 1,
  limit: 20,
  pages: 1,
};

const CREATE_PAYLOAD: PersonCreate = {
  first_name: 'Alice',
  last_name: 'Martin',
  gender: 'female',
  is_living: true,
  privacy_level: 'private',
};

// ── Suite ──────────────────────────────────────────────────────────────────────

describe('PersonService', () => {
  let service: PersonService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [PersonService],
    });

    service = TestBed.inject(PersonService);
    http    = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  // ── list() ──────────────────────────────────────────────────────────────────

  describe('list()', () => {
    it('appelle GET /persons/ avec les params page et limit par défaut', () => {
      service.list().subscribe();

      const req = http.expectOne((r) => r.url === `${API}/persons/`);
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('page')).toBe('1');
      expect(req.request.params.get('limit')).toBe('20');
      req.flush(MOCK_LIST);
    });

    it('passe les paramètres de pagination personnalisés', () => {
      service.list(3, 50).subscribe();

      const req = http.expectOne((r) => r.url === `${API}/persons/`);
      expect(req.request.params.get('page')).toBe('3');
      expect(req.request.params.get('limit')).toBe('50');
      req.flush({ ...MOCK_LIST, page: 3, limit: 50 });
    });

    it('inclut le paramètre search quand fourni', () => {
      service.list(1, 20, 'Dupont').subscribe();

      const req = http.expectOne((r) => r.url === `${API}/persons/`);
      expect(req.request.params.get('search')).toBe('Dupont');
      req.flush(MOCK_LIST);
    });

    it('n\'inclut PAS search quand il est vide', () => {
      service.list(1, 20, '').subscribe();

      const req = http.expectOne((r) => r.url === `${API}/persons/`);
      expect(req.request.params.has('search')).toBeFalse();
      req.flush(MOCK_LIST);
    });

    it('n\'inclut PAS search quand il ne contient que des espaces', () => {
      service.list(1, 20, '   ').subscribe();

      const req = http.expectOne((r) => r.url === `${API}/persons/`);
      expect(req.request.params.has('search')).toBeFalse();
      req.flush(MOCK_LIST);
    });

    it('retourne un PersonListResponse avec items, total, page, limit, pages', (done) => {
      service.list().subscribe((res) => {
        expect(res.items.length).toBe(1);
        expect(res.total).toBe(1);
        expect(res.page).toBe(1);
        expect(res.limit).toBe(20);
        expect(res.pages).toBe(1);
        done();
      });
      http.expectOne((r) => r.url === `${API}/persons/`).flush(MOCK_LIST);
    });

    it('retourne une liste vide quand aucun membre', (done) => {
      service.list().subscribe((res) => {
        expect(res.items).toEqual([]);
        expect(res.total).toBe(0);
        done();
      });
      http.expectOne((r) => r.url === `${API}/persons/`)
        .flush({ items: [], total: 0, page: 1, limit: 20, pages: 1 });
    });
  });

  // ── get() ────────────────────────────────────────────────────────────────────

  describe('get()', () => {
    it('appelle GET /persons/:id avec l\'ID correct', () => {
      service.get('person-1').subscribe();

      const req = http.expectOne(`${API}/persons/person-1`);
      expect(req.request.method).toBe('GET');
      req.flush(MOCK_PERSON);
    });

    it('retourne la personne dans l\'observable', (done) => {
      service.get('person-1').subscribe((person) => {
        expect(person.id).toBe('person-1');
        expect(person.first_name).toBe('Jean');
        expect(person.last_name).toBe('Dupont');
        done();
      });
      http.expectOne(`${API}/persons/person-1`).flush(MOCK_PERSON);
    });

    it('inclut tous les champs de la personne', (done) => {
      service.get('person-1').subscribe((person) => {
        expect(person.gender).toBe('male');
        expect(person.birth_date).toBe('1990-01-15');
        expect(person.privacy_level).toBe('private');
        done();
      });
      http.expectOne(`${API}/persons/person-1`).flush(MOCK_PERSON);
    });
  });

  // ── create() ─────────────────────────────────────────────────────────────────

  describe('create()', () => {
    it('appelle POST /persons/ avec le bon payload', () => {
      service.create(CREATE_PAYLOAD).subscribe();

      const req = http.expectOne(`${API}/persons/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(CREATE_PAYLOAD);
      req.flush({ ...MOCK_PERSON, ...CREATE_PAYLOAD });
    });

    it('retourne la personne créée dans l\'observable', (done) => {
      const created: Person = { ...MOCK_PERSON, ...CREATE_PAYLOAD, id: 'new-id' };

      service.create(CREATE_PAYLOAD).subscribe((person) => {
        expect(person.id).toBe('new-id');
        expect(person.first_name).toBe('Alice');
        done();
      });
      http.expectOne(`${API}/persons/`).flush(created);
    });

    it('envoie first_name et last_name comme champs obligatoires', () => {
      service.create({ first_name: 'Bob', last_name: 'Smith', privacy_level: 'private', is_living: true }).subscribe();

      const req = http.expectOne(`${API}/persons/`);
      expect(req.request.body.first_name).toBe('Bob');
      expect(req.request.body.last_name).toBe('Smith');
      req.flush(MOCK_PERSON);
    });

    it('transmet les champs optionnels quand fournis', () => {
      const payload: PersonCreate = {
        ...CREATE_PAYLOAD,
        birth_date: '2000-05-15',
        birth_place: 'Lyon',
        occupation: 'Ingénieur',
      };
      service.create(payload).subscribe();

      const req = http.expectOne(`${API}/persons/`);
      expect(req.request.body.birth_date).toBe('2000-05-15');
      expect(req.request.body.occupation).toBe('Ingénieur');
      req.flush(MOCK_PERSON);
    });
  });

  // ── update() ─────────────────────────────────────────────────────────────────

  describe('update()', () => {
    it('appelle PUT /persons/:id avec le bon payload', () => {
      service.update('person-1', { first_name: 'Pierre' }).subscribe();

      const req = http.expectOne(`${API}/persons/person-1`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ first_name: 'Pierre' });
      req.flush({ ...MOCK_PERSON, first_name: 'Pierre' });
    });

    it('retourne la personne mise à jour', (done) => {
      service.update('person-1', { first_name: 'Pierre' }).subscribe((person) => {
        expect(person.first_name).toBe('Pierre');
        done();
      });
      http.expectOne(`${API}/persons/person-1`).flush({ ...MOCK_PERSON, first_name: 'Pierre' });
    });

    it('utilise l\'ID fourni dans l\'URL', () => {
      service.update('other-id-456', { last_name: 'Test' }).subscribe();

      const req = http.expectOne(`${API}/persons/other-id-456`);
      expect(req.request.url).toContain('other-id-456');
      req.flush(MOCK_PERSON);
    });

    it('peut mettre à jour plusieurs champs simultanément', () => {
      service.update('person-1', {
        first_name: 'Marie',
        last_name: 'Curie',
        is_living: false,
      }).subscribe();

      const req = http.expectOne(`${API}/persons/person-1`);
      expect(req.request.body.first_name).toBe('Marie');
      expect(req.request.body.last_name).toBe('Curie');
      expect(req.request.body.is_living).toBeFalse();
      req.flush(MOCK_PERSON);
    });
  });

  // ── delete() ─────────────────────────────────────────────────────────────────

  describe('delete()', () => {
    it('appelle DELETE /persons/:id', () => {
      service.delete('person-1').subscribe();

      const req = http.expectOne(`${API}/persons/person-1`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });

    it('utilise l\'ID correct dans l\'URL', () => {
      service.delete('target-uuid-789').subscribe();

      const req = http.expectOne(`${API}/persons/target-uuid-789`);
      expect(req.request.url).toContain('target-uuid-789');
      req.flush(null);
    });

    it('ne passe aucun body dans la requête DELETE', () => {
      service.delete('person-1').subscribe();

      const req = http.expectOne(`${API}/persons/person-1`);
      expect(req.request.body).toBeNull();
      req.flush(null);
    });

    it('complète l\'observable après suppression (void)', (done) => {
      service.delete('person-1').subscribe({
        next: () => { /* void, pas de valeur */ },
        complete: done,
      });
      http.expectOne(`${API}/persons/person-1`).flush(null);
    });
  });
});
