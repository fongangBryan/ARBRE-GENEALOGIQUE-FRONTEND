import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { Router } from '@angular/router';

import { AuthService } from './auth.service';
import { User } from '../models/user.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

// ── Données de test ────────────────────────────────────────────────────────────

const MOCK_USER: User = {
  id: 'user-1',
  email: 'test@example.com',
  first_name: 'Jean',
  last_name: 'Dupont',
  role: 'editor',
  is_active: true,
  is_verified: true,
  is_2fa_enabled: false,
  created_at: '2024-01-01T00:00:00Z',
  last_login: null,
};

const MOCK_TOKENS = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
};

// ── Suite ──────────────────────────────────────────────────────────────────────

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    routerSpy = jasmine.createSpyObj<Router>('Router', ['navigate']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Router, useValue: routerSpy },
      ],
    });

    service = TestBed.inject(AuthService);
    http    = TestBed.inject(HttpTestingController);

    // Nettoyer localStorage avant chaque test
    localStorage.clear();
  });

  afterEach(() => {
    http.verify(); // vérifie qu'il n'y a pas de requêtes HTTP en attente
    localStorage.clear();
  });

  // ── login() ─────────────────────────────────────────────────────────────────

  describe('login()', () => {
    it('appelle POST /auth/login avec email et password', () => {
      service.login({ email: 'test@test.com', password: 'pass' }).subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'test@test.com', password: 'pass' });
      req.flush({ ...MOCK_TOKENS, requires_2fa: false });
    });

    it('stocke les tokens dans localStorage après succès', () => {
      service.login({ email: 'test@test.com', password: 'pass' }).subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      req.flush({ ...MOCK_TOKENS, requires_2fa: false });

      expect(localStorage.getItem('access_token')).toBe(MOCK_TOKENS.access_token);
      expect(localStorage.getItem('refresh_token')).toBe(MOCK_TOKENS.refresh_token);
    });

    it('positionne isLoggedIn à true après succès', () => {
      service.login({ email: 'test@test.com', password: 'pass' }).subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      req.flush({ ...MOCK_TOKENS, requires_2fa: false });

      expect(service.isLoggedIn()).toBeTrue();
    });

    it('ne stocke PAS les tokens si requires_2fa est true', () => {
      service.login({ email: 'test@test.com', password: 'pass' }).subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      req.flush({ access_token: '', refresh_token: '', requires_2fa: true, user_id: 'u1' });

      expect(localStorage.getItem('access_token')).toBeNull();
      expect(service.isLoggedIn()).toBeFalse();
    });

    it('stocke les credentials 2FA en attente si requires_2fa est true', () => {
      service.login({ email: 'user@test.com', password: 'secret' }).subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      req.flush({ access_token: '', refresh_token: '', requires_2fa: true, user_id: 'u1' });

      expect(service.pending2faCreds()).toEqual({
        email: 'user@test.com',
        password: 'secret',
      });
    });
  });

  // ── verify2fa() ─────────────────────────────────────────────────────────────

  describe('verify2fa()', () => {
    it('appelle POST /auth/login avec les credentials en attente + code TOTP', () => {
      // Simuler un état 2FA en attente
      service['pending2faCreds'].set({ email: 'user@test.com', password: 'secret' });

      service.verify2fa('123456').subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      expect(req.request.body).toEqual({
        email: 'user@test.com',
        password: 'secret',
        two_factor_code: '123456',
      });
      req.flush({ ...MOCK_TOKENS, requires_2fa: false });
    });

    it('stocke les tokens et isLoggedIn après validation 2FA', () => {
      service['pending2faCreds'].set({ email: 'u@t.com', password: 'p' });

      service.verify2fa('654321').subscribe();

      const req = http.expectOne(`${API}/auth/login`);
      req.flush({ ...MOCK_TOKENS, requires_2fa: false });

      expect(service.isLoggedIn()).toBeTrue();
      expect(localStorage.getItem('access_token')).toBe(MOCK_TOKENS.access_token);
    });

    it('réinitialise pending2faCreds après validation', () => {
      service['pending2faCreds'].set({ email: 'u@t.com', password: 'p' });

      service.verify2fa('000000').subscribe();
      http.expectOne(`${API}/auth/login`).flush({ ...MOCK_TOKENS, requires_2fa: false });

      expect(service.pending2faCreds()).toBeNull();
    });

    it('lève une erreur si aucun credentials 2FA en attente', () => {
      expect(() => service.verify2fa('123456')).toThrowError();
    });
  });

  // ── register() ──────────────────────────────────────────────────────────────

  describe('register()', () => {
    const REGISTER_PAYLOAD = {
      email: 'new@test.com',
      password: 'pass',
      first_name: 'Alice',
      last_name: 'Martin',
    };

    it('appelle POST /auth/register avec le bon payload', () => {
      service.register(REGISTER_PAYLOAD).subscribe();

      const req = http.expectOne(`${API}/auth/register`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(REGISTER_PAYLOAD);
      req.flush(MOCK_TOKENS);
    });

    it('stocke les tokens après inscription', () => {
      service.register(REGISTER_PAYLOAD).subscribe();
      http.expectOne(`${API}/auth/register`).flush(MOCK_TOKENS);

      expect(localStorage.getItem('access_token')).toBe(MOCK_TOKENS.access_token);
      expect(localStorage.getItem('refresh_token')).toBe(MOCK_TOKENS.refresh_token);
    });

    it('positionne isLoggedIn à true après inscription', () => {
      service.register(REGISTER_PAYLOAD).subscribe();
      http.expectOne(`${API}/auth/register`).flush(MOCK_TOKENS);

      expect(service.isLoggedIn()).toBeTrue();
    });
  });

  // ── fetchCurrentUser() ───────────────────────────────────────────────────────

  describe('fetchCurrentUser()', () => {
    it('appelle GET /users/me', () => {
      service.fetchCurrentUser().subscribe();

      const req = http.expectOne(`${API}/users/me`);
      expect(req.request.method).toBe('GET');
      req.flush(MOCK_USER);
    });

    it('positionne currentUser avec la réponse', () => {
      service.fetchCurrentUser().subscribe();
      http.expectOne(`${API}/users/me`).flush(MOCK_USER);

      const user = service.currentUser();
      expect(user).not.toBeNull();
      expect(user?.email).toBe(MOCK_USER.email);
      expect(user?.role).toBe('editor');
    });

    it('retourne l\'utilisateur dans l\'observable', (done) => {
      service.fetchCurrentUser().subscribe((user) => {
        expect(user.id).toBe(MOCK_USER.id);
        done();
      });
      http.expectOne(`${API}/users/me`).flush(MOCK_USER);
    });
  });

  // ── navigateByRole() ─────────────────────────────────────────────────────────

  describe('navigateByRole()', () => {
    it('navigue vers /admin pour le rôle admin', () => {
      service['currentUser'].set({ ...MOCK_USER, role: 'admin' });
      service.navigateByRole();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/admin']);
    });

    it('navigue vers /dashboard pour le rôle editor', () => {
      service['currentUser'].set({ ...MOCK_USER, role: 'editor' });
      service.navigateByRole();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/dashboard']);
    });

    it('navigue vers /dashboard pour le rôle reader', () => {
      service['currentUser'].set({ ...MOCK_USER, role: 'reader' });
      service.navigateByRole();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/dashboard']);
    });

    it('navigue vers /dashboard si aucun utilisateur connecté', () => {
      service['currentUser'].set(null);
      service.navigateByRole();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/dashboard']);
    });
  });

  // ── logout() ─────────────────────────────────────────────────────────────────

  describe('logout()', () => {
    beforeEach(() => {
      localStorage.setItem('access_token', 'tok');
      localStorage.setItem('refresh_token', 'ref');
      service['isLoggedIn'].set(true);
      service['currentUser'].set(MOCK_USER);
    });

    it('supprime les tokens du localStorage', () => {
      service.logout();
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    it('positionne isLoggedIn à false', () => {
      service.logout();
      expect(service.isLoggedIn()).toBeFalse();
    });

    it('réinitialise currentUser à null', () => {
      service.logout();
      expect(service.currentUser()).toBeNull();
    });

    it('navigue vers /login', () => {
      service.logout();
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
    });
  });

  // ── refreshTokens() ──────────────────────────────────────────────────────────

  describe('refreshTokens()', () => {
    it('appelle POST /auth/refresh avec le refresh_token', () => {
      service.refreshTokens('old-refresh-token').subscribe();

      const req = http.expectOne(`${API}/auth/refresh`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ refresh_token: 'old-refresh-token' });
      req.flush(MOCK_TOKENS);
    });

    it('met à jour les tokens dans localStorage', () => {
      service.refreshTokens('old-token').subscribe();
      http.expectOne(`${API}/auth/refresh`).flush({
        access_token: 'new-access',
        refresh_token: 'new-refresh',
      });

      expect(localStorage.getItem('access_token')).toBe('new-access');
      expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
    });

    it('retourne le nouveau access_token dans l\'observable', (done) => {
      service.refreshTokens('old').subscribe((token) => {
        expect(token).toBe('new-access-token');
        done();
      });
      http.expectOne(`${API}/auth/refresh`).flush({
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      });
    });
  });

  // ── getToken() ───────────────────────────────────────────────────────────────

  describe('getToken()', () => {
    it('retourne null si aucun token en localStorage', () => {
      expect(service.getToken()).toBeNull();
    });

    it('retourne le token stocké', () => {
      localStorage.setItem('access_token', 'my-token');
      expect(service.getToken()).toBe('my-token');
    });
  });

  // ── forgotPassword() ─────────────────────────────────────────────────────────

  describe('forgotPassword()', () => {
    it('appelle POST /auth/forgot-password avec l\'email', () => {
      service.forgotPassword('user@test.com').subscribe();

      const req = http.expectOne(`${API}/auth/forgot-password`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'user@test.com' });
      req.flush({ message: 'Email envoyé' });
    });
  });

  // ── resetPassword() ──────────────────────────────────────────────────────────

  describe('resetPassword()', () => {
    it('appelle POST /auth/reset-password avec token et nouveau mot de passe', () => {
      service.resetPassword('reset-token-xyz', 'NewPass123!').subscribe();

      const req = http.expectOne(`${API}/auth/reset-password`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        token: 'reset-token-xyz',
        new_password: 'NewPass123!',
      });
      req.flush({ message: 'Mot de passe réinitialisé' });
    });
  });

  // ── verifyEmail() ─────────────────────────────────────────────────────────────

  describe('verifyEmail()', () => {
    it('appelle POST /auth/verify-email avec le token en query param', () => {
      service.verifyEmail('email-token-abc').subscribe();

      const req = http.expectOne(`${API}/auth/verify-email?token=email-token-abc`);
      expect(req.request.method).toBe('POST');
      req.flush({ message: 'Email vérifié' });
    });
  });

  // ── resendVerification() ──────────────────────────────────────────────────────

  describe('resendVerification()', () => {
    it('appelle POST /auth/resend-verification', () => {
      service.resendVerification().subscribe();

      const req = http.expectOne(`${API}/auth/resend-verification`);
      expect(req.request.method).toBe('POST');
      req.flush({ message: 'Email renvoyé' });
    });
  });
});
