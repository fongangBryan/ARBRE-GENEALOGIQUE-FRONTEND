import { Component, inject, signal, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

function passwordsMatch(ctrl: AbstractControl): ValidationErrors | null {
  const pw  = ctrl.get('new_password')?.value;
  const cnf = ctrl.get('confirm')?.value;
  return pw && cnf && pw !== cnf ? { mismatch: true } : null;
}

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './reset-password.html',
  styleUrl: './reset-password.css',
})
export class ResetPasswordComponent implements OnInit {
  private fb    = inject(FormBuilder);
  private auth  = inject(AuthService);
  private route = inject(ActivatedRoute);

  token = signal('');

  form = this.fb.group({
    new_password: ['', [Validators.required, Validators.minLength(8)]],
    confirm:      ['', Validators.required],
  }, { validators: passwordsMatch });

  loading = signal(false);
  done    = signal(false);
  error   = signal<string | null>(null);
  showPw  = signal(false);

  get pw()  { return this.form.get('new_password')!; }
  get cnf() { return this.form.get('confirm')!; }

  togglePw() { this.showPw.update(v => !v); }

  ngOnInit() {
    const t = this.route.snapshot.queryParamMap.get('token') ?? '';
    this.token.set(t);
    if (!t) this.error.set('Lien invalide ou expiré.');
  }

  submit() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    this.auth.resetPassword(this.token(), this.pw.value!).subscribe({
      next: () => { this.loading.set(false); this.done.set(true); },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Lien invalide ou expiré.');
      },
    });
  }
}
