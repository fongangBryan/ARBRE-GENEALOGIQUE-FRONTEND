import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class LoginComponent {
  private fb      = inject(FormBuilder);
  private router  = inject(Router);
  private auth    = inject(AuthService);

  form = this.fb.group({
    email:    ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  loading     = signal(false);
  error       = signal<string | null>(null);
  showPass    = signal(false);
  needs2fa    = signal(false);
  userId      = signal<string | null>(null);

  get email()    { return this.form.get('email')!; }
  get password() { return this.form.get('password')!; }

  togglePass() { this.showPass.update(v => !v); }

  submit() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }

    this.loading.set(true);
    this.error.set(null);

    this.auth.login(this.form.getRawValue() as any).subscribe({
      next: res => {
        if (res.requires_2fa) {
          this.needs2fa.set(true);
          this.userId.set(res.user_id ?? null);
          this.loading.set(false);
        } else {
          this.router.navigate(['/dashboard']);
        }
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Email ou mot de passe incorrect.');
      },
    });
  }
}
