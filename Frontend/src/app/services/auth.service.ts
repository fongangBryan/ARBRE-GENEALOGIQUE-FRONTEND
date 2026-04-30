import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap, switchMap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { LoginRequest, LoginResponse, RegisterRequest, TokenResponse } from '../models/auth.model';
import { User } from '../models/user.model';

const API = 'http://localhost:8080/api/v1';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http   = inject(HttpClient);
  private router = inject(Router);

  isLoggedIn   = signal(!!localStorage.getItem('access_token'));
  currentUser  = signal<User | null>(null);
  pending2faCreds = signal<{ email: string; password: string } | null>(null);

  login(body: LoginRequest) {
    return this.http.post<LoginResponse>(`${API}/auth/login`, body).pipe(
      tap(res => {
        if (res.requires_2fa) {
          this.pending2faCreds.set({ email: body.email, password: body.password });
        } else {
          this.storeTokens(res.access_token!, res.refresh_token!);
          this.isLoggedIn.set(true);
        }
      })
    );
  }

  verify2fa(code: string): Observable<LoginResponse> {
    const creds = this.pending2faCreds();
    if (!creds) throw new Error('No pending 2FA credentials');
    const body = { ...creds, two_factor_code: code };
    return this.http.post<LoginResponse>(`${API}/auth/login`, body).pipe(
      tap(res => {
        this.storeTokens(res.access_token!, res.refresh_token!);
        this.isLoggedIn.set(true);
        this.pending2faCreds.set(null);
      })
    );
  }

  register(body: RegisterRequest) {
    return this.http.post<TokenResponse>(`${API}/auth/register`, body).pipe(
      tap(res => {
        this.storeTokens(res.access_token, res.refresh_token);
        this.isLoggedIn.set(true);
      })
    );
  }

  fetchCurrentUser(): Observable<User> {
    return this.http.get<User>(`${API}/users/me`).pipe(
      tap(user => this.currentUser.set(user))
    );
  }

  navigateByRole() {
    const user = this.currentUser();
    if (user?.role === 'admin') {
      this.router.navigate(['/admin']);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.isLoggedIn.set(false);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  getToken() { return localStorage.getItem('access_token'); }

  private storeTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
}
