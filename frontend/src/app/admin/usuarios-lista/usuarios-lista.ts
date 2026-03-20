import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { jwtDecode } from 'jwt-decode';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-usuarios-lista',
  templateUrl: './usuarios-lista.html',
  styleUrls: ['./usuarios-lista.scss'],
  standalone: true,
  imports: [CommonModule]
})
export class UsuariosLista implements OnInit {
  public listaUsuarios: any[] = [];
  public userName: string = '';
  private apiUrl = environment.apiUrl;

  constructor(
    private http: HttpClient, 
    private router: Router,
    private cd: ChangeDetectorRef // <--- Agregado para forzar el refresco visual
  ) {}

  ngOnInit() {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded: any = jwtDecode(token);
        this.userName = decoded.sub;
      } catch (e) {
        console.error("Error en token", e);
      }
    }
    this.cargarUsuarios();
  }

  cargarUsuarios() {
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);

    console.log("Solicitando usuarios al backend...");
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-usuarios`, { headers })
      .subscribe({
        next: (res) => {
          console.log('Usuarios cargados desde el servidor:', res);
          this.listaUsuarios = res; 
          this.cd.detectChanges(); // <--- OBLIGATORIO: Avisa a Angular que ya hay datos
        },
        error: (err) => {
          console.error('Error de conexión', err);
          if (err.status === 403) alert('No tienes permisos de Administrador.');
        }
      });
  }

  // Traducción actualizada a tu nueva jerarquía (0-4)
  getRoleName(rolId: number): string {
    const roles: { [key: number]: string } = {
      0: 'SuperAdministrador',
      1: 'Administrador',
      2: 'Archivista (Gestión TRD)',
      3: 'Radicador / Operario',
      4: 'Consultor / Búsqueda'
    };
    return roles[rolId] || 'Usuario Externo';
  }

  getRoleClass(rolId: number): string {
    const classes: { [key: number]: string } = {
      0: 'role-super',
      1: 'role-admin',
      2: 'role-archivista',
      3: 'role-radicador',
      4: 'role-consultor'
    };
    return classes[rolId] || 'role-default';
  }

  toggleEstadoUsuario(user: any) {
    const nuevoEstado = !user.activo;
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    
    const formData = new FormData();
    formData.append('usuario_id', user.id.toString());
    formData.append('activar', nuevoEstado.toString());

    this.http.post(`${this.apiUrl}/admin/toggle-usuario`, formData, { headers })
      .subscribe({
        next: (res: any) => {
          user.activo = nuevoEstado;
          this.cd.detectChanges();
        },
        error: (err) => alert('Error: ' + (err.error?.detail || 'Fallo de red'))
      });
  }

  regresar() {
    this.router.navigate(['/dashboard']);
  }
}