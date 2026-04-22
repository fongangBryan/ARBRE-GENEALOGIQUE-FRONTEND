import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';
import { LoginRequest, LoginResponse, RegisterRequest, TokenResponse } from '../models/auth.model';

const API = 'http://localhost:8000/api/v1';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http   = inject(HttpClient);
  private router = inject(Router);

  isLoggedIn = signal(!!localStorage.getItem('access_token'));

  login(body: LoginRequest) {
    return this.http.post<LoginResponse>(`${API}/auth/login`, body).pipe(
      tap(res => {
        if (!res.requires_2fa) {
          this.storeTokens(res.access_token, res.refresh_token);
          this.isLoggedIn.set(true);
        }
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

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.isLoggedIn.set(false);
    this.router.navigate(['/login']);
  }

  getToken() { return localStorage.getItem('access_token'); }

  private storeTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
}
