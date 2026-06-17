import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../../shared/services/toast.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let message = 'An unexpected error occurred';
      if (error.status === 0)   message = 'Cannot reach server — is the backend running?';
      if (error.status === 404) message = error.error?.error ?? 'Resource not found';
      if (error.status === 422) message = error.error?.error ?? 'Validation error';
      if (error.status === 500) message = 'Internal server error';

      toast.show(message);
      return throwError(() => new Error(message));
    })
  );
};
