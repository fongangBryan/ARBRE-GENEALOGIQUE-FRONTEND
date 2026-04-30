import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map, catchError, of } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { UserRole } from '../../models/user.model';

export function roleGuard(allowedRoles: UserRole[]): CanActivateFn {
  return () => {
    const auth   = inject(AuthService);
    const router = inject(Router);

    if (!auth.isLoggedIn()) return router.createUrlTree(['/login']);

    const user = auth.currentUser();
    if (user) {
      return allowedRoles.includes(user.role) ? true : router.createUrlTree(['/dashboard']);
    }

    return auth.fetchCurrentUser().pipe(
      map(u => allowedRoles.includes(u.role) ? true : router.createUrlTree(['/dashboard'])),
      catchError(() => of(router.createUrlTree(['/login'])))
    );
  };
}
