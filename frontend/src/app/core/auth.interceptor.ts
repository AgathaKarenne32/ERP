import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/**
 * Functional interceptor: attaches the access token to API calls and, on a 401,
 * tries once to refresh the token (via the httpOnly cookie) and replays the
 * request. Auth endpoints themselves are skipped to avoid refresh loops.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const isAuthCall = req.url.includes('/api/auth/');

  const token = auth.token();
  const authed =
    token && !isAuthCall
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

  return next(authed).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !isAuthCall && token) {
        return auth.refresh().pipe(
          switchMap((res) =>
            next(req.clone({ setHeaders: { Authorization: `Bearer ${res.access_token}` } })),
          ),
          catchError((refreshErr) => {
            auth.logout();
            return throwError(() => refreshErr);
          }),
        );
      }
      return throwError(() => err);
    }),
  );
};
