import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError, shareReplay, tap } from 'rxjs';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';

// Shared observable — all concurrent 401s wait for the same single refresh call
let refresh$: Observable<string> | null = null;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth  = inject(AuthService);
  const token = localStorage.getItem('access_token');

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      // Don't intercept non-401 errors or auth endpoints (avoid infinite loops)
      if (err.status !== 401 || req.url.includes('/auth/')) {
        return throwError(() => err);
      }

      const rt = localStorage.getItem('refresh_token');
      if (!rt) {
        auth.logout();
        return throwError(() => err);
      }

      // Create a single shared refresh observable for all concurrent failures
      if (!refresh$) {
        refresh$ = auth.refreshTokens(rt).pipe(
          tap({ next: () => { refresh$ = null; }, error: () => { refresh$ = null; } }),
          shareReplay(1)
        );
      }

      return refresh$.pipe(
        switchMap(newToken =>
          next(req.clone({ setHeaders: { Authorization: `Bearer ${newToken}` } }))
        ),
        catchError(() => {
          auth.logout();
          return throwError(() => err);
        })
      );
    })
  );
};
