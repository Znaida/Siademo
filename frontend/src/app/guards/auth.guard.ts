import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';

export const authGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const token = localStorage.getItem('token');

  if (token) {
    return true;
  } else {
    // Redirigimos al login pasando un parámetro de 'error'
    router.navigate(['/login'], { queryParams: { auth: 'denied' } });
    return false;
  }
};