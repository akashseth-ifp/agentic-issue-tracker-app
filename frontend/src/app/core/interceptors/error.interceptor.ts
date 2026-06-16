import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let message = 'An unexpected error occurred';
      if (error.status === 0)   message = 'Cannot reach server — is the backend running?';
      if (error.status === 404) message = error.error?.error ?? 'Resource not found';
      if (error.status === 422) message = error.error?.error ?? 'Validation error';
      if (error.status === 500) message = 'Internal server error';
      console.error(`[HTTP ${error.status}]`, message);
      return throwError(() => new Error(message));
    })
  );
};
