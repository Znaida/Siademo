import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { timeout, finalize } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.scss'],
  standalone: false
})
export class Login implements OnInit {
  // --- VARIABLES DE ESTADO ---
  public captchaPregunta: string = '';
  public paso2: boolean = false;
  public cargando: boolean = false;
  public mensajeSeguridad: boolean = false;
  public modoReset: boolean = false;
  public resetExitoso: boolean = false;
  public resetError: string = '';

  public loginData = {
    usuario: '',
    password: '',
    captchaRespuesta: null as number | null,
    captchaToken: '',
    codigo2fa: ''
  };

  public resetData = {
    token: '',
    password_nuevo: '',
    password_confirmar: ''
  };

  private apiUrl = environment.apiUrl;

  constructor(
    private http: HttpClient, 
    private router: Router,
    private route: ActivatedRoute,
    private cd: ChangeDetectorRef   
  ) {}

  ngOnInit() {
    // Limpiamos rastro de sesión previa
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('debe_cambiar_password');
    this.obtenerCaptcha();

    this.route.queryParams.subscribe(params => {
      if (params['auth'] === 'denied') {
        this.mensajeSeguridad = true;
        this.cd.detectChanges();
      }
    });
  }

  // --- GESTIÓN DE RETO MATEMÁTICO ---
  obtenerCaptcha() {
    this.captchaPregunta = ''; // Reseteamos para que el HTML muestre "Cargando..."
    
    this.http.get<any>(`${this.apiUrl}/auth/captcha`).subscribe({
      next: (res) => {
        // Asignamos la pregunta (ej: "4 + 8")
        this.captchaPregunta = res.pregunta; 
        
        // Guardamos el token en el objeto loginData
        this.loginData.captchaToken = res.captcha_token; 
        
        // console.log("Reto de integridad cargado:", res.pregunta);
        this.cd.detectChanges();
      },
      error: (err) => {
        console.error("Error de conexión al servidor de seguridad:", err);
        this.mensajeSeguridad = true;
        this.cd.detectChanges();
      }
    });
  }

  intentarLogin(event: Event) {
    event.preventDefault(); 
    
    if (this.cargando) return;
    this.cargando = true;
    this.cd.detectChanges();

    // AJUSTE: Las rutas reales en main.py llevan el prefijo /auth/
    const endpoint = !this.paso2 ? 'auth/login' : 'auth/verify-2fa';
    
    const formData = new FormData();
    formData.append('usuario', this.loginData.usuario);

    if (!this.paso2) {
      // PASO 1: Credenciales + Captcha
      formData.append('password', this.loginData.password);
      formData.append('captcha_res', (this.loginData.captchaRespuesta ?? 0).toString());
      formData.append('captcha_token', this.loginData.captchaToken);
    } else {
      // PASO 2: Verificación TOTP
      formData.append('codigo', this.loginData.codigo2fa);
    }

    this.http.post<any>(`${this.apiUrl}/${endpoint}`, formData)
      .pipe(
        timeout(8000), 
        finalize(() => {
          this.cargando = false;
          this.cd.detectChanges();
        })
      )
      .subscribe({
        next: (res) => {
          if (!this.paso2) {
            this.paso2 = true;
            console.log("Credenciales correctas. Solicitando 2FA.");
          } else {
            // ÉXITO: Guardamos JWT y entramos a SIADE
            localStorage.setItem('token', res.access_token);
            localStorage.setItem('refresh_token', res.refresh_token || '');
            localStorage.setItem('debe_cambiar_password', res.debe_cambiar_password ? '1' : '0');
            this.router.navigate(['/dashboard']);
          }
          this.cd.detectChanges();
        },
        error: (err) => {
          alert(err.error?.detail || "Fallo en la autenticación.");
          if (!this.paso2) {
            this.loginData.captchaRespuesta = null;
            this.obtenerCaptcha();
          }
          this.cd.detectChanges();
        }
      });
  }

  abrirReset() {
    this.modoReset = true;
    this.resetExitoso = false;
    this.resetError = '';
    this.resetData = { token: '', password_nuevo: '', password_confirmar: '' };
  }

  volverLogin() {
    this.modoReset = false;
    this.resetExitoso = false;
    this.resetError = '';
  }

  enviarReset(event: Event) {
    event.preventDefault();
    if (this.cargando) return;
    this.resetError = '';

    if (this.resetData.password_nuevo !== this.resetData.password_confirmar) {
      this.resetError = 'Las contraseñas no coinciden.';
      return;
    }
    if (this.resetData.password_nuevo.length < 8) {
      this.resetError = 'La contraseña debe tener al menos 8 caracteres.';
      return;
    }

    this.cargando = true;
    const formData = new FormData();
    formData.append('token', this.resetData.token.trim());
    formData.append('password_nuevo', this.resetData.password_nuevo);
    formData.append('password_confirmar', this.resetData.password_confirmar);

    this.http.post<any>(`${this.apiUrl}/auth/reset-password`, formData)
      .pipe(finalize(() => { this.cargando = false; this.cd.detectChanges(); }))
      .subscribe({
        next: () => { this.resetExitoso = true; this.cd.detectChanges(); },
        error: (err) => { this.resetError = err.error?.detail || 'Error al restablecer la contraseña.'; this.cd.detectChanges(); }
      });
  }
}