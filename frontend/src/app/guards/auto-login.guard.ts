import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';

/**
 * AutoLogin guard: si el usuario ya tiene token y navega a /login,
 * lo redirige directamente al dashboard sin mostrar el formulario.
 */
export const autoLoginGuard: CanActivateFn = () => {
  const router = inject(Router);
  const token = localStorage.getItem('token');

  if (token) {
    router.navigate(['/dashboard']);
    return false;
  }
  return true;
};
