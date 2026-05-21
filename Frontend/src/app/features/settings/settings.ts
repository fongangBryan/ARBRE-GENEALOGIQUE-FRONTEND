import { Component, inject, signal, OnInit, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AppShellComponent } from '../../shared/components/app-shell/app-shell';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user.model';
import { environment } from '../../../environments/environment';

const API = environment.apiUrl;

type Msg = { type: 'success' | 'error'; text: string } | null;

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [AppShellComponent, FormsModule, ReactiveFormsModule],
  templateUrl: './settings.html',
  styleUrl: './settings.css',
})
export class SettingsComponent implements OnInit {
  private http = inject(HttpClient);
  private fb   = inject(FormBuilder);
  readonly auth = inject(AuthService);

  user           = signal<User | null>(null);
  savingProfile    = signal(false);
  savingPwd        = signal(false);
  saving2fa        = signal(false);
  sendingVerif     = signal(false);
  profileMsg       = signal<Msg>(null);
  pwdMsg           = signal<Msg>(null);
  twoFaMsg         = signal<Msg>(null);
  verifMsg         = signal<Msg>(null);

  qrCode       = signal<string | null>(null);
  twoFaSecret  = signal<string | null>(null);
  twoFaToken   = signal('');
  disableToken = signal('');
  showDisable  = signal(false);

  profileForm = this.fb.group({
    first_name: [''],
    last_name:  [''],
  });

  pwdForm = this.fb.group({
    current_password: ['', Validators.required],
    new_password:     ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', Validators.required],
  }, {
    validators: (g: AbstractControl) => {
      const np = g.get('new_password')?.value;
      const cp = g.get('confirm_password')?.value;
      return np && cp && np !== cp ? { mismatch: true } : null;
    }
  });

  ngOnInit() {
    const cur = this.auth.currentUser();
    if (cur) {
      this.user.set(cur);
      this.profileForm.patchValue({ first_name: cur.first_name ?? '', last_name: cur.last_name ?? '' });
    } else {
      this.auth.fetchCurrentUser().subscribe({
        next: u => {
          this.user.set(u);
          this.profileForm.patchValue({ first_name: u.first_name ?? '', last_name: u.last_name ?? '' });
        }
      });
    }
  }

  saveProfile() {
    this.savingProfile.set(true);
    const v = this.profileForm.getRawValue();
    this.http.put<User>(`${API}/users/me`, { first_name: v.first_name, last_name: v.last_name }).subscribe({
      next: u => {
        this.auth.currentUser.set(u);
        this.user.set(u);
        this.savingProfile.set(false);
        this.flash(this.profileMsg, 'success', 'Profil mis Ã  jour avec succÃ¨s.');
      },
      error: err => {
        this.savingProfile.set(false);
        this.flash(this.profileMsg, 'error', err.error?.detail ?? 'Erreur lors de la mise Ã  jour.');
      }
    });
  }

  changePassword() {
    if (this.pwdForm.invalid) { this.pwdForm.markAllAsTouched(); return; }
    this.savingPwd.set(true);
    const v = this.pwdForm.getRawValue();
    this.http.put(`${API}/users/me/password`, {
      current_password: v.current_password,
      new_password: v.new_password
    }).subscribe({
      next: () => {
        this.savingPwd.set(false);
        this.pwdForm.reset();
        this.flash(this.pwdMsg, 'success', 'Mot de passe modifiÃ© avec succÃ¨s.');
      },
      error: err => {
        this.savingPwd.set(false);
        this.flash(this.pwdMsg, 'error', err.error?.detail ?? 'Mot de passe actuel incorrect.');
      }
    });
  }

  setup2fa() {
    this.saving2fa.set(true);
    this.http.post<{ qr_code: string; secret: string }>(`${API}/auth/setup-2fa`, {}).subscribe({
      next: r => {
        this.saving2fa.set(false);
        this.qrCode.set('data:image/png;base64,' + r.qr_code);
        this.twoFaSecret.set(r.secret);
      },
      error: err => {
        this.saving2fa.set(false);
        this.flash(this.twoFaMsg, 'error', err.error?.detail ?? 'Erreur lors de la configuration 2FA.');
      }
    });
  }

  verify2fa() {
    const token = this.twoFaToken().trim();
    if (token.length !== 6) return;
    this.saving2fa.set(true);
    this.http.post<{ message: string }>(`${API}/auth/verify-2fa`, { token }).subscribe({
      next: () => {
        this.saving2fa.set(false);
        this.qrCode.set(null);
        this.twoFaSecret.set(null);
        this.twoFaToken.set('');
        this.user.update(u => u ? { ...u, is_2fa_enabled: true } : u);
        this.flash(this.twoFaMsg, 'success', 'Double authentification activÃ©e.');
      },
      error: err => {
        this.saving2fa.set(false);
        this.flash(this.twoFaMsg, 'error', err.error?.detail ?? 'Code invalide. RÃ©essayez.');
      }
    });
  }

  disable2fa() {
    const token = this.disableToken().trim();
    if (token.length !== 6) return;
    this.saving2fa.set(true);
    this.http.post<{ message: string }>(`${API}/auth/disable-2fa`, { token }).subscribe({
      next: () => {
        this.saving2fa.set(false);
        this.showDisable.set(false);
        this.disableToken.set('');
        this.user.update(u => u ? { ...u, is_2fa_enabled: false } : u);
        this.flash(this.twoFaMsg, 'success', 'Double authentification dÃ©sactivÃ©e.');
      },
      error: err => {
        this.saving2fa.set(false);
        this.flash(this.twoFaMsg, 'error', err.error?.detail ?? 'Code invalide. RÃ©essayez.');
      }
    });
  }

  resendVerification() {
    this.sendingVerif.set(true);
    this.auth.resendVerification().subscribe({
      next: () => {
        this.sendingVerif.set(false);
        this.flash(this.verifMsg, 'success', 'Email de vérification envoyé. Consultez votre boîte de réception.');
      },
      error: err => {
        this.sendingVerif.set(false);
        this.flash(this.verifMsg, 'error', err.error?.detail ?? 'Erreur lors de l\'envoi.');
      },
    });
  }

  cancelSetup() {
    this.qrCode.set(null);
    this.twoFaSecret.set(null);
    this.twoFaToken.set('');
  }

  userInitials(): string {
    const u = this.user();
    return ((u?.first_name?.[0] ?? '') + (u?.last_name?.[0] ?? '')).toUpperCase() || (u?.email?.[0] ?? '?').toUpperCase();
  }

  roleLabel(role: string): string {
    const m: Record<string, string> = { admin: 'Administrateur', editor: 'Ã‰diteur', reader: 'Lecteur' };
    return m[role] ?? role;
  }

  private flash(sig: WritableSignal<Msg>, type: 'success' | 'error', text: string) {
    sig.set({ type, text });
    setTimeout(() => sig.set(null), 4500);
  }
}

