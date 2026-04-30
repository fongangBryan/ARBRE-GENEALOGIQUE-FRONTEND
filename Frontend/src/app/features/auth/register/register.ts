import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

function passwordsMatch(g: AbstractControl): ValidationErrors | null {
  const pw  = g.get('password')?.value;
  const cpw = g.get('confirmPassword')?.value;
  return pw && cpw && pw !== cpw ? { mismatch: true } : null;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrl: './register.css',
})
export class RegisterComponent {
  private fb   = inject(FormBuilder);
  private auth = inject(AuthService);

  form = this.fb.group({
    first_name:      ['', [Validators.required, Validators.minLength(2)]],
    last_name:       ['', [Validators.required, Validators.minLength(2)]],
    email:           ['', [Validators.required, Validators.email]],
    password:        ['', [Validators.required, Validators.minLength(8), Validators.pattern(/^(?=.*[A-Z])(?=.*\d).+$/)]],
    confirmPassword: ['', Validators.required],
    terms:           [false, Validators.requiredTrue],
  }, { validators: passwordsMatch });

  loading  = signal(false);
  error    = signal<string | null>(null);
  showPass = signal(false);
  showConf = signal(false);

  get firstName()       { return this.form.get('first_name')!; }
  get lastName()        { return this.form.get('last_name')!; }
  get email()           { return this.form.get('email')!; }
  get password()        { return this.form.get('password')!; }
  get confirmPassword() { return this.form.get('confirmPassword')!; }
  get terms()           { return this.form.get('terms')!; }

  toggleShowPass() { this.showPass.update(v => !v); }
  toggleShowConf() { this.showConf.update(v => !v); }

  get strength(): 0 | 1 | 2 | 3 {
    const pw = this.password.value ?? '';
    if (pw.length === 0) return 0;
    let s = 0;
    if (pw.length >= 8)   s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/\d/.test(pw))    s++;
    return s as 0 | 1 | 2 | 3;
  }

  get strengthLabel() { return ['', 'Faible', 'Moyen', 'Fort'][this.strength]; }
  get strengthClass() { return ['', 'weak', 'medium', 'strong'][this.strength]; }

  submit() {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }

    this.loading.set(true);
    this.error.set(null);

    const { first_name, last_name, email, password } = this.form.getRawValue();
    this.auth.register({ first_name: first_name!, last_name: last_name!, email: email!, password: password! }).subscribe({
      next: () => {
        this.auth.fetchCurrentUser().subscribe({
          next: () => this.auth.navigateByRole(),
          error: () => this.auth.navigateByRole(),
        });
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Une erreur est survenue. Veuillez réessayer.');
      },
    });
  }
}
