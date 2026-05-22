import { Component, inject, signal, computed, ElementRef, ViewChildren, QueryList, AfterViewInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-two-factor',
  standalone: true,
  imports: [],
  templateUrl: './two-factor.html',
  styleUrl: './two-factor.css',
})
export class TwoFactorComponent implements AfterViewInit {
  @ViewChildren('digitInput') digitInputs!: QueryList<ElementRef<HTMLInputElement>>;

  private router = inject(Router);
  private auth   = inject(AuthService);

  digits     = signal<string[]>(['', '', '', '', '', '']);
  codeComplete = computed(() => this.digits().every(d => d !== ''));
  loading = signal(false);
  error   = signal<string | null>(null);

  ngAfterViewInit() {
    this.digitInputs.first?.nativeElement.focus();
  }

  onInput(index: number, event: Event) {
    const input = event.target as HTMLInputElement;
    const val   = input.value.replace(/\D/g, '').slice(-1);
    input.value = val;

    const updated = [...this.digits()];
    updated[index] = val;
    this.digits.set(updated);

    if (val && index < 5) {
      this.digitInputs.get(index + 1)?.nativeElement.focus();
    }

    if (updated.every(d => d !== '')) {
      this.submit();
    }
  }

  onKeydown(index: number, event: KeyboardEvent) {
    if (event.key === 'Backspace' && !this.digits()[index] && index > 0) {
      const updated = [...this.digits()];
      updated[index - 1] = '';
      this.digits.set(updated);
      this.digitInputs.get(index - 1)?.nativeElement.focus();
    }
  }

  onPaste(event: ClipboardEvent) {
    event.preventDefault();
    const text = event.clipboardData?.getData('text') ?? '';
    const nums  = text.replace(/\D/g, '').slice(0, 6).split('');
    const updated = ['', '', '', '', '', ''];
    nums.forEach((n, i) => { updated[i] = n; });
    this.digits.set(updated);
    this.digitInputs.forEach((el, i) => { el.nativeElement.value = updated[i]; });
    const next = Math.min(nums.length, 5);
    this.digitInputs.get(next)?.nativeElement.focus();
    if (updated.every(d => d !== '')) this.submit();
  }

  submit() {
    const code = this.digits().join('');
    if (code.length < 6) return;

    this.loading.set(true);
    this.error.set(null);

    this.auth.verify2fa(code).subscribe({
      next: () => {
        this.auth.fetchCurrentUser().subscribe({
          next: () => this.auth.navigateByRole(),
          error: () => this.auth.navigateByRole(),
        });
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Code invalide. Veuillez réessayer.');
        this.digits.set(['', '', '', '', '', '']);
        this.digitInputs.forEach(el => { el.nativeElement.value = ''; });
        this.digitInputs.first?.nativeElement.focus();
      },
    });
  }

  backToLogin() { this.router.navigate(['/login']); }
}
