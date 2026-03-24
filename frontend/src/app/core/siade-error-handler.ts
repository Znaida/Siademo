import { ErrorHandler, Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

/**
 * ErrorHandler personalizado para SIADE.
 * Los HttpErrorResponse ya son manejados en los componentes (error callbacks),
 * por lo que no deben re-loguearse globalmente.
 * Solo se loguean errores inesperados de la aplicación.
 */
@Injectable()
export class SiadeErrorHandler implements ErrorHandler {
  handleError(error: any): void {
    // HttpErrorResponse: manejado en cada componente — ignorar aquí
    if (error instanceof HttpErrorResponse) return;

    // Errores envueltos por zone.js ("Uncaught (in promise)")
    if (error?.rejection instanceof HttpErrorResponse) return;

    // Cualquier otro error inesperado sí se loguea
    console.error('[SIADE Error]', error);
  }
}
