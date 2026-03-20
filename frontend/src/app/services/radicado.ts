import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class RadicadoService {
  private url = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getRadicados(): Observable<any[]> {
    return this.http.get<any[]>(`${this.url}/radicados`);
  }

  // Esta función es la que enviará el PDF y los datos a Python
  crearRadicado(datos: FormData): Observable<any> {
    return this.http.post(`${this.url}/radicar`, datos);
  }
}