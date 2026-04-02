import { Injectable } from '@angular/core';
import {
  HttpInterceptor, HttpRequest, HttpHandler,
  HttpEvent, HttpErrorResponse, HTTP_INTERCEPTORS
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  // Evita múltiples llamadas simultáneas al refresh
  private refreshing = false;
  private refreshSubject = new BehaviorSubject<string | null>(null);

  constructor(private http: HttpClient, private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // No interceptar la llamada al propio refresh (evita bucle infinito)
    if (req.url.includes('/auth/refresh') || req.url.includes('/auth/login') || req.url.includes('/auth/captcha')) {
      return next.handle(req);
    }

    const token = localStorage.getItem('token');
    const reqConToken = token ? this.agregarToken(req, token) : req;

    return next.handle(reqConToken).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          return this.manejarExpiracion(req, next);
        }
        return throwError(() => error);
      })
    );
  }

  private agregarToken(req: HttpRequest<any>, token: string): HttpRequest<any> {
    return req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }

  private manejarExpiracion(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const refreshToken = localStorage.getItem('refresh_token');

    // Sin refresh token ni token de acceso: nunca hubo sesión — no redirigir
    const tokenActual = localStorage.getItem('token');
    if (!refreshToken && !tokenActual) {
      return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Unauthorized' }));
    }

    // Tenía token pero expiró y no hay refresh — sesión caducada, redirigir con aviso
    if (!refreshToken) {
      this.cerrarSesion();
      return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Session expired' }));
    }

    if (this.refreshing) {
      // Esperar a que termine el refresh en curso
      return this.refreshSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap(token => next.handle(this.agregarToken(req, token!)))
      );
    }

    this.refreshing = true;
    this.refreshSubject.next(null);

    const formData = new FormData();
    formData.append('refresh_token', refreshToken);

    return this.http.post<any>(`${environment.apiUrl}/auth/refresh`, formData).pipe(
      switchMap(res => {
        this.refreshing = false;
        const nuevoToken = res.access_token;
        localStorage.setItem('token', nuevoToken);
        if (res.refresh_token) {
          localStorage.setItem('refresh_token', res.refresh_token);
        }
        this.refreshSubject.next(nuevoToken);
        return next.handle(this.agregarToken(req, nuevoToken));
      }),
      catchError(err => {
        this.refreshing = false;
        this.cerrarSesion();
        return throwError(() => err);
      })
    );
  }

  private cerrarSesion() {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('debe_cambiar_password');
    this.router.navigate(['/login'], { queryParams: { auth: 'expired' } });
  }
}
