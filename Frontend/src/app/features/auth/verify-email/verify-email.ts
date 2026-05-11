import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './verify-email.html',
  styleUrl: './verify-email.css',
})
export class VerifyEmailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private auth  = inject(AuthService);

  status = signal<'loading' | 'success' | 'error'>('loading');
  error  = signal<string | null>(null);

  ngOnInit() {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.status.set('error');
      this.error.set('Lien de vérification invalide.');
      return;
    }
    this.auth.verifyEmail(token).subscribe({
      next: () => this.status.set('success'),
      error: err => {
        this.status.set('error');
        this.error.set(err.error?.detail ?? 'Lien invalide ou expiré.');
      },
    });
  }
}
