import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { jwtDecode } from 'jwt-decode';
import { interval, Subscription } from 'rxjs';
import Swal from 'sweetalert2';
import { jsPDF } from 'jspdf';
import QRCode from 'qrcode';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
  standalone: false
})
export class Dashboard implements OnInit, OnDestroy {
  // --- ESTADO DEL USUARIO ---
  userRole: number = 0;
  userId: number = 0;
  userName: string = '';
  userRoleName: string = '';
  userInitials: string = '';
  pasoCreacionGrupo: number = 1; // 1: Formulario, 2: Éxito

  // --- CONTROL DE NAVEGACIÓN PRINCIPAL ---
  seccionActiva: string = 'dashboard'; 
  tabActivaVentanilla: string = 'recibidas';
  tabActivaConfig: string = 'datos-usuarios';
  busquedaGlobal: string = '';

  // --- VARIABLES DE VENTANILLA (RADICACIÓN) ---
  radicado = {
    tipoRemitente: 'Natural', // natural o juridica
    primerApellido: '',
    segundoApellido: '',
    nombreRemitente: '', // nombre o razon social
    tipoDocRemitente: 'Cédula de Ciudadanía',
    nroDocRemitente: '',
    cargo: '',
    direccion: '',
    telefono: '',
    correo: '',
    pais: 'Colombia',
    departamento: 'Caldas',
    ciudad: 'Manizales',
    serie: '',
    subserie: '',
    tipoDocumental: '',
    asunto: '',
    metodoRecepcion: 'Portal Web',
    nroGuia: '',
    folios: 1,
    diasRespuesta: 15,
    fechaVencimiento: '2026-03-19', // Calculado
    anexoNombre: '',       // Corresponde a 'Anexo'
    descripcionAnexo: '',  // Corresponde a 'Descripción del anexo'
    seccionResponsable: '',
    funcionarioResponsable: '',
    conCopia: '',
    seccionOrigen: '',          // Sección que envía
    funcionarioOrigen: '',
    nroRadicadoRelacionado: '', // Para el "Enlace de radicado recibido"
    activaFlujoId: null as number | null         // Para vincular al flujo de trabajo
  };



  fechaActualRadicado: string = ''; // Fecha y hora automática
  nroRadicadoSimulado: string = '00123'; // Para el preview

  // --- VARIABLES PARA ADJUNTOS ---
nombreArchivoPrincipal: string = '';
nombreArchivoAnexo: string = '';
archivoBinarioPrincipal: File | null = null;
anexosBinarios: File[] = [];

  // --- CONFIGURACIÓN DEL MENÚ DINÁMICO ---
  menuItems = [
    { label: 'Dashboard', icon: '📈', roles: [0, 1, 2, 3] },
    { label: 'Ventanilla Única', icon: '📥', roles: [0, 1, 2] },
    { label: 'Configuración', icon: '⚙️', roles: [0, 1] },
    { label: 'Gestión Documental', icon: '📁', roles: [0, 1, 2] },
    { label: 'Flujos de Trabajo', icon: '🌿', roles: [0, 1] },
    { label: 'Archivo Central', icon: '📦', roles: [0, 1] },
    { label: 'Informes', icon: '📊', roles: [0, 1] }
  ];

  // --- LÓGICA DE NAVEGACIÓN ---
  ejecutarAccion(label: string, rolesPermitidos: number[]) {
    // 1. Validación de seguridad: Verifica si el rol tiene permiso
    if (!this.tieneAcceso(rolesPermitidos)) {
      console.warn(`Acceso denegado para ${label}`);
      alert("⚠️ No tienes permisos para acceder a esta sección.");
      return;
    }

    // 2. Control de navegación: Cambia la sección activa
    switch(label) {
      case 'Dashboard':
        this.seccionActiva = 'dashboard';
        break;

      case 'Configuración':
        this.seccionActiva = 'configuracion';
        this.tabActivaConfig = 'estructura-organica'; // Tab inicial por defecto
        break;

      case 'Ventanilla Única':
        this.seccionActiva = 'ventanilla';
        this.tabActivaVentanilla = 'recibidas';
        break;

      case 'Gestión Documental':
        this.seccionActiva = 'gestion-documental';
        this.cargarRadicados();
        break;

      case 'Archivo Central':
        this.seccionActiva = 'archivo-central';
        this.buscarArchivoCentral();
        break;

      default:
        // Manejo para secciones en desarrollo (Informes, Archivo Central, etc.)
        alert(`La sección de ${label} está en desarrollo.`);
        break;
    }

    // 3. Forzamos la detección de cambios para actualizar la interfaz
    setTimeout(() => this.cd.detectChanges(), 0);
  }

  // Función para cambiar pestañas de ventanilla
  cambiarTabVentanilla(tab: string) {
    this.tabActivaVentanilla = tab;
    this.cd.detectChanges();
  }

  // --- MATRIZ DE ROLES DE USUARIO ---
  rolesParametrizacion = [
    //{ ESTO HAY QE QUITARLO PARA QUE NO APAREZCA EN LA INSPECCION
      //nombre: 'Super Usuario',
      //nivel: 'Nivel 0',
      //color: '#2563eb',
      //permisos: ['Control total del sistema (Informático)', 'Creación y eliminación de usuarios', 'Auditoría forense de registros']
    //},
    {
      nombre: 'Administrador',
      nivel: 'Nivel 1',
      color: '#7c3aed',
      permisos: ['Carga/Descarga de Tablas de Configuración', 'Gestión de Sedes, Unidades y Oficinas', 'Administración de TRD (Series/Subseries)', 'Diseño de flujos y anulación de registros']
    },
    {
      nombre: 'Usuario Productor',
      nivel: 'Nivel 2',
      color: '#d97706',
      permisos: ['Aprobar y Trasladar documentos', 'Remitir y Archivar correspondencia', 'Devolver e Imprimir registros oficiales']
    },
    {
      nombre: 'Usuario Consultor',
      nivel: 'Nivel 3',
      color: '#64748b',
      permisos: ['Búsqueda y consulta de documentos', 'Visualización de expedientes públicos', 'Generación de reportes básicos']
    }
  ];

  // --- ESTRUCTURA ORGÁNICA (Niveles 1 y 2) ---
  entidadInfo = {
    nombre: 'Alcaldía de Manizales',
    fondoSeleccionado: 'Gestión Administrativa',
    fondosDisponibles: ['Gestión Administrativa', 'Archivo Central', 'Académico'],
    sedes: 'Manizales, Chinchiná, Pereira'
  };

  nuevaDependencia = {
    unidadNombre: '',
    oficinaNombre: '',
    unidadRelacionada: ''
  };

  unidadesDisponibles: string[] = ['Planeación', 'Finanzas'];
  unidadesOrganicas: any[] = [
    { unidad: 'Planeación', oficina: 'Secretaría General' },
    { unidad: 'Finanzas', oficina: 'Tesorería' }
  ];

  // --- GESTIÓN DE TRD (Completa) ---
  nuevaTRD = {
    codUnidad: '', unidad: '', codOficina: '', oficina: '',
    codSerie: '', nombreSerie: '', codSubserie: '', nombreSubserie: '',
    tipoDocumental: '', soporte: 'Digital', extension: 'PDF',
    gestion: 0, central: 0, disposicion: 'Conservación Total',
    porcentaje: 0, procedimiento: '',
    llaves: ['', '', '', ''] // Llaves de búsqueda dinámicas capturadas
  };

  listaTRD: any[] = [
    { codigo: '1.01', unidad: 'Gerencia', serie: 'Acciones Constitucionales', subserie: 'Acciones de Tutela', soporte: 'Papel', ag: 2, ac: 20, disposicion: 'Eliminación' }
  ];
  
  // --- CONTROL DE INTERFAZ (Modales) ---
  mostrarFormularioCrear: boolean = false; 
  mostrarModalUsuarios: boolean = false;   
  mostrarModalConfig: boolean = false; 

// --- [AJUSTADO] ESTADOS PARA GRUPOS DE TRABAJO ---
  mostrarModalCrearGrupo: boolean = false; // Modal del Dashboard
  mostrarModalAsignarGrupo: boolean = false; // Modal de la Tabla (Checkboxes)
  nombreNuevoGrupo: string = ''; 
  usuarioSeleccionado: any = null; 
  
  tipoSeleccionado: string = 'RAD';     
  
  // --- ALMACENAMIENTO DE DATOS ---
  listaUsuarios: any[] = [];
  eventosRecientes: any[] = [];
  listaRadicados: any[] = [];
  busquedaRadicados: string = '';
  filtrosGestion = { tipo: '', estado: '', serie: '', vencido: '' };
  // --- ARCHIVO CENTRAL ---
  listaArchivoCentral: any[] = [];
  filtrosArchivo = { q: '', anio: 0, serie: '', caja: '', disposicion: '' };
  mostrarModalTransferencia: boolean = false;
  radicadoATransferir: any = null;
  transferenciaData = { caja: '', carpeta: '', folio_inicio: null as number|null, folio_fin: null as number|null, llaves_busqueda: '', observaciones: '' };
  usuariosActivos: any[] = [];
  notificaciones: any[] = [];
  // --- MODALES FLUJO ---
  mostrarModalTraslado: boolean = false;
  mostrarModalHistorial: boolean = false;
  cargandoHistorial: boolean = false;
  radicadoSeleccionado: any = null;
  historialActual: any[] = [];
  trasladoNuevoResponsableId: number | null = null;
  trasladoComentario: string = '';
  archivarComentario: string = '';
  
 // --- [AJUSTADO] ALMACENAMIENTO PARA GRUPOS ---
  listaEquipos: any[] = []; // Listado de grupos para los checkboxes
  userParaAsignar: any = null;

  private auditSubscription?: Subscription;

  nuevoUser = {
    nombre: '',
    usuario: '',
    password: '',
    rol_id: 3 
  };

  private apiUrl = environment.apiUrl;

  constructor(
    private router: Router, 
    private http: HttpClient,
    private cd: ChangeDetectorRef 
  ) {}

  ngOnInit() {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded: any = jwtDecode(token);
        this.userRole = decoded.rol;
        this.userId = decoded.id_usuario;
        this.userName = decoded.sub || 'Usuario';
        this.userRoleName = this.getRoleName(this.userRole);
        this.userInitials = this.userName.substring(0, 1).toUpperCase();

        // Inicializar fecha de radicación
        const ahora = new Date();
        this.fechaActualRadicado = ahora.toLocaleString('es-CO', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });

        // Carga inicial de datos persistentes
        this.cargarEstructura();
        this.cargarTRD();
        this.cargarListaGrupos();
        this.cargarUsuariosActivos();
        this.cargarNotificaciones();

        if (this.userRole <= 1) {
          this.iniciarMonitoreo();
        }
      } catch (error) {
        this.cerrarSesion();
      }
    } else {
      this.router.navigate(['/login']);
    }
  }

  
  // --- SEGURIDAD: HELPER PARA HEADERS JWT ---
  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders().set('Authorization', `Bearer ${token}`);
  }

  // --- LÓGICA DE NAVEGACIÓN Y PERMISOS ---

  tieneAcceso(rolesPermitidos: number[]): boolean {
    return rolesPermitidos.includes(this.userRole);
  }

  cambiarTabConfig(tab: string) {
    this.tabActivaConfig = tab;
    if (tab === 'datos-usuarios') {
      this.cargarUsuarios();
    }
    if (tab === 'estructura-organica') {
      this.cargarEstructura();
    }
    if (tab === 'trd') {
      this.cargarTRD();
    }
  }

  

  // --- GESTIÓN DE ESTRUCTURA ORGÁNICA (VÍNCULO CON FASTAPI) ---

  cargarEstructura() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-estructura`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.unidadesOrganicas = res;
          this.unidadesDisponibles = [...new Set(res.map(u => u.unidad))];
          this.cd.detectChanges();
        },
        error: () => console.warn("Modo local: No se pudo cargar la estructura.")
      });
  }

  agregarDependencia() {
    if (!this.nuevaDependencia.unidadNombre || !this.nuevaDependencia.oficinaNombre) {
      alert("⚠️ Error: Debes completar la Unidad y la Oficina.");
      return;
    }

    // MAPEO SEGÚN PYDANTIC EN EL BACKEND
    const payload = {
      entidad: this.entidadInfo.nombre,
      unidad_administrativa: this.nuevaDependencia.unidadNombre,
      oficina_productora: this.nuevaDependencia.oficinaNombre,
      relacion_jerarquica: this.nuevaDependencia.unidadRelacionada || 'Nivel Raíz'
    };

    console.log("%c--- ENVIANDO ESTRUCTURA A SQL ---", "color: #2563eb; font-weight: bold;");
    
    this.http.post(`${this.apiUrl}/admin/registrar-dependencia`, payload, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res: any) => {
          alert("✅ Estructura vinculada y guardada en PostgreSQL.");
          this.cargarEstructura(); // Sincronizamos con la DB
          this.nuevaDependencia = { unidadNombre: '', oficinaNombre: '', unidadRelacionada: '' };
          this.cd.detectChanges();
        },
        error: (err) => {
          alert("❌ Error en el servidor: " + (err.error?.detail || "Fallo de conexión"));
        }
      });
  }

  editarUnidad(index: number) {
    console.log("Editando unidad:", this.unidadesOrganicas[index]);
  }

  eliminarUnidad(index: number) {
    if(confirm("¿Seguro que desea eliminar esta unidad administrativa?")) {
      this.unidadesOrganicas.splice(index, 1);
    }
  }

  ejecutarRadicacion() {
    // 1. Validación de campos obligatorios
    if (!this.radicado.nombreRemitente || !this.radicado.asunto) {
      alert("⚠️ Error: El nombre del remitente/destinatario y el asunto son obligatorios.");
      return;
    }

    // 2. Validación de archivo principal (Requisito técnico para SIADE)
    if (!this.archivoBinarioPrincipal) {
      alert("⚠️ Error: Debe adjuntar el documento digitalizado principal.");
      return;
    }

    console.log("%c--- INICIANDO PROCESO DE RADICACIÓN OFICIAL ---", "color: #2563eb; font-weight: bold;");

    // 3. Mapeo de Metadata: De Angular (CamelCase) a Python (SnakeCase)
    const metadata = {
      //tipo_radicado: this.tabActivaVentanilla === 'recibidas' ? 'RECIBIDA' : 'ENVIADA',
      tipo_radicado: this.tabActivaVentanilla.toUpperCase(), // Asegura INTERNA
      tipo_remitente: this.radicado.tipoRemitente,
      primer_apellido: this.radicado.primerApellido,
      segundo_apellido: this.radicado.segundoApellido,
      nombre_razon_social: this.radicado.nombreRemitente,
      tipo_documento: this.radicado.tipoDocRemitente,
      nro_documento: this.radicado.nroDocRemitente,
      cargo: this.radicado.cargo,
      direccion: this.radicado.direccion,
      telefono: this.radicado.telefono,
      correo_electronico: this.radicado.correo,
      pais: this.radicado.pais,
      departamento: this.radicado.departamento,
      ciudad: this.radicado.ciudad,
      serie: this.radicado.serie,
      subserie: this.radicado.subserie,
      tipo_documental: this.radicado.tipoDocumental,
      asunto: this.radicado.asunto,
      seccion_origen: this.radicado.seccionOrigen,
      funcionario_origen_id: 1, // ID del usuario actual (origen)
      metodo_recepcion: this.radicado.metodoRecepcion,
      nro_guia: this.radicado.nroGuia,
      nro_folios: this.radicado.folios,
      dias_respuesta: this.radicado.diasRespuesta,
      seccion_responsable: this.radicado.seccionResponsable,
      funcionario_responsable_id: 1, // ID del usuario que firma (luego hacerlo dinámico)
      con_copia: this.radicado.conCopia,
      // Campos de trazabilidad y flujo
      nro_radicado_relacionado: this.radicado.nroRadicadoRelacionado,
      activa_flujo_id: this.radicado.activaFlujoId
    };

    // 4. Preparación del paquete de envío (FormData para archivos + JSON)
    const formData = new FormData();
    formData.append('metadata', JSON.stringify(metadata)); // La metadata viaja como string JSON
    formData.append('archivo_principal', this.archivoBinarioPrincipal);
    
    // Agregar múltiples anexos si existen
    if (this.anexosBinarios.length > 0) {
      this.anexosBinarios.forEach((file) => {
        formData.append('anexos', file);
      });
    }

    // 5. Envío al Backend (FastAPI)
    this.http.post<any>(`${this.apiUrl}/radicar`, formData, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.nroRadicadoSimulado = res.numero;
          this.limpiarFormularioRadicacion();
          this.obtenerEventos();
          Swal.fire({
            icon: 'success',
            title: '¡Radicado Generado!',
            html: `
              <div style="text-align:left; font-family: 'Inter', sans-serif; line-height: 2;">
                <p><strong>N° Radicado:</strong> <span style="color:#2563eb; font-size:1.1rem; font-weight:900;">${res.numero}</span></p>
                <p><strong>Fecha Vencimiento:</strong> ${res.vencimiento}</p>
              </div>
            `,
            showCancelButton: true,
            confirmButtonText: '🖨️ Imprimir Sticker',
            cancelButtonText: '← Volver',
            confirmButtonColor: '#2563eb',
            cancelButtonColor: '#64748b',
            allowOutsideClick: false,
          }).then((result) => {
            if (result.isConfirmed) {
              this.imprimirStickerPDF(res.numero, res.vencimiento);
            }
          });
        },
        error: (err) => {
          console.error("Error en radicación:", err);
          Swal.fire({
            icon: 'error',
            title: 'Error en Radicación',
            text: err.error?.detail || 'Fallo en la comunicación con el motor SIADE.',
            confirmButtonText: '← Volver',
            confirmButtonColor: '#ef4444'
          });
        }
      });
  }

async imprimirStickerPDF(nroRadicado: string, vencimiento: string) {
    const labelMap: Record<string, string> = {
      'recibidas':    'ALCALDÍA DE MANIZALES (ENTRADA)',
      'enviadas':     'ALCALDÍA DE MANIZALES (SALIDA)',
      'internas':     'ALCALDÍA DE MANIZALES (INTERNA)',
      'no-radicables':'ALCALDÍA DE MANIZALES (NO RADICABLE)'
    };
    const label = labelMap[this.tabActivaVentanilla] ?? 'ALCALDÍA DE MANIZALES';

    const qrData = `SIADE|${nroRadicado}|${new Date().toISOString()}`;
    const qrDataUrl: string = await QRCode.toDataURL(qrData, { width: 200, margin: 1 });

    const doc = new jsPDF({ unit: 'mm', format: [80, 100] });

    // Fondo header
    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, 80, 18, 'F');

    doc.setTextColor(255, 255, 255);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('S  I  A  D  E', 40, 7, { align: 'center' });
    doc.setFontSize(5.5);
    doc.setFont('helvetica', 'normal');
    doc.text(label, 40, 13, { align: 'center' });

    // Número de radicado
    doc.setTextColor(37, 99, 235);
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text(nroRadicado, 40, 27, { align: 'center' });

    // QR
    doc.addImage(qrDataUrl, 'PNG', 22, 31, 36, 36);

    // Línea separadora
    doc.setDrawColor(226, 232, 240);
    doc.line(5, 70, 75, 70);

    // Datos
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');

    const isInterna = this.tabActivaVentanilla === 'internas';
    if (isInterna) {
      doc.text('Remite:', 5, 76);
      doc.setFont('helvetica', 'normal');
      doc.text(this.radicado.funcionarioOrigen || '---', 25, 76);
      doc.setFont('helvetica', 'bold');
      doc.text('Destino:', 5, 82);
      doc.setFont('helvetica', 'normal');
      doc.text(this.radicado.funcionarioResponsable || '---', 25, 82);
    } else {
      const personLabel = this.tabActivaVentanilla === 'enviadas' ? 'Destinatario:' : 'Remitente:';
      doc.text(personLabel, 5, 76);
      doc.setFont('helvetica', 'normal');
      doc.text(this.radicado.nombreRemitente || '---', 30, 76);
      doc.setFont('helvetica', 'bold');
      doc.text('Vencimiento:', 5, 82);
      doc.setFont('helvetica', 'normal');
      doc.text(vencimiento, 30, 82);
    }

    doc.setFont('helvetica', 'bold');
    doc.text('Fecha:', 5, 88);
    doc.setFont('helvetica', 'normal');
    doc.text(this.fechaActualRadicado, 25, 88);

    doc.save(`sticker_${nroRadicado}.pdf`);
  }

// Función auxiliar para limpiar tras el éxito
limpiarFormularioRadicacion() {
  // Reiniciar el objeto radicado con todos sus campos vacíos
  this.radicado = {
    tipoRemitente: 'Natural',
    primerApellido: '',
    segundoApellido: '',
    nombreRemitente: '', 
    tipoDocRemitente: 'Cédula de Ciudadanía',
    nroDocRemitente: '',
    cargo: '',
    direccion: '',
    telefono: '',
    correo: '',
    pais: 'Colombia',
    departamento: 'Caldas',
    ciudad: 'Manizales',
    serie: '',
    subserie: '',
    tipoDocumental: '',
    asunto: '',
    metodoRecepcion: 'Portal Web',
    nroGuia: '',
    folios: 1,
    diasRespuesta: 15,
    fechaVencimiento: '',
    anexoNombre: '',       // Corresponde a 'Anexo'
    descripcionAnexo: '',  // Corresponde a 'Descripción del anexo'
    seccionResponsable: '',
    funcionarioResponsable: '',
    conCopia: '',
    seccionOrigen: '',          // Sección que envía
    funcionarioOrigen: '',
    // Campos exclusivos de Enviadas/Trazabilidad
    nroRadicadoRelacionado: '',
    activaFlujoId: null
  };

  // Limpiar estados de archivos
  this.nombreArchivoPrincipal = '';
  this.nombreArchivoAnexo = '';
  this.archivoBinarioPrincipal = null;
  this.anexosBinarios = [];
  
  this.cd.detectChanges();
}

  // --- GESTIÓN DE TRD (VÍNCULO CON FASTAPI Y JSONB) ---

  cargarTRD() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-trd`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.listaTRD = res;
          console.log("TRD Cargada para el formulario:", this.listaTRD); // <--- Mira esto en F12
          this.cd.detectChanges();
        },
        error: () => console.warn("Error al cargar TRD para la ventanilla.")
      });
  }

  agregarALaTRD() {
    if (!this.nuevaTRD.codSerie || !this.nuevaTRD.nombreSerie) {
      alert("Por favor complete el código y nombre de la serie.");
      return;
    }

    // MAPEO SEGÚN PYDANTIC (TRDCreate)
    const payloadTRD = {
      codigo_completo: `${this.nuevaTRD.codSerie}${this.nuevaTRD.codSubserie ? '.' + this.nuevaTRD.codSubserie : ''}`,
      unidad: this.nuevaTRD.unidad,
      oficina: this.nuevaTRD.oficina,
      serie: this.nuevaTRD.nombreSerie,
      subserie: this.nuevaTRD.nombreSubserie || null,
      soporte: this.nuevaTRD.soporte,
      gestion_anios: this.nuevaTRD.gestion,
      central_anios: this.nuevaTRD.central,
      disposicion: this.nuevaTRD.disposicion,
      llaves_busqueda: this.nuevaTRD.llaves // SE ENVIARÁ COMO JSONB A POSTGRESQL
    };

    console.log("%c--- ENVIANDO TRD A BACKEND ---", "color: #7c3aed; font-weight: bold;");

    this.http.post(`${this.apiUrl}/admin/registrar-trd`, payloadTRD, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res: any) => {
          alert("✅ Serie documental indexada en la TRD exitosamente.");
          this.cargarTRD(); // Refrescamos la tabla desde SQL
          
          // Limpieza de campos específicos
          this.nuevaTRD.codSerie = '';
          this.nuevaTRD.nombreSerie = '';
          this.nuevaTRD.codSubserie = '';
          this.nuevaTRD.nombreSubserie = '';
          
          this.cd.detectChanges();
        },
        error: (err) => {
          alert("❌ Error al guardar TRD: " + (err.error?.detail || "Fallo del motor SIADE"));
        }
      });
  }

// --- [NUEVA LÓGICA] GESTIÓN DE GRUPOS (UNIFICADA) ---

  abrirModalCrearGrupo() {
    this.pasoCreacionGrupo = 1;
    this.nombreNuevoGrupo = '';
    this.mostrarModalCrearGrupo = true;
    this.cd.detectChanges();
  }

  crearGrupoUnico() {
    const nombreLimpio = this.nombreNuevoGrupo.trim();
    if (!nombreLimpio) {
      alert("⚠️ Escribe un nombre para el grupo.");
      return;
    }

    const duplicado = this.listaEquipos.some(g => g.nombre.toLowerCase() === nombreLimpio.toLowerCase());
    if (duplicado) {
      alert(`❌ El grupo "${nombreLimpio}" ya existe.`);
      return;
    }

    const payload = { nombre: nombreLimpio };
    this.http.post(`${this.apiUrl}/admin/crear-equipo`, payload, { headers: this.getAuthHeaders() })
      .subscribe({
        next: () => {
          this.pasoCreacionGrupo = 2; // <--- CAMBIAMOS AL PASO DE ÉXITO
          this.cargarListaGrupos(); 
          this.cd.detectChanges();
        },
        error: (err) => alert("Error: " + err.error?.detail)
      });
  }

  abrirAsignacionGrupos(user: any) {
    this.usuarioSeleccionado = user;
    console.log(`%c--- CARGANDO GRUPOS PARA: ${user.nombre_completo} ---`, "color: #7c3aed; font-weight: bold;");

    this.http.get<any[]>(`${this.apiUrl}/admin/listar-equipos`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.listaEquipos = res.map(g => ({ ...g, seleccionado: false }));
          this.mostrarModalAsignarGrupo = true;
          this.cd.detectChanges();
        },
        error: () => alert("⚠️ No hay grupos disponibles.")
      });
  }

  guardarAsignacionMasiva() {
    const seleccionados = this.listaEquipos.filter(g => g.seleccionado).map(g => g.id);
    
    const payload = {
      usuario_id: this.usuarioSeleccionado.id,
      equipos_ids: seleccionados
    };

    this.http.post(`${this.apiUrl}/admin/asignar-equipos-usuario`, payload, { headers: this.getAuthHeaders() })
      .subscribe({
        next: () => {
          alert(`✅ Grupos vinculados a ${this.usuarioSeleccionado.nombre_completo}`);
          this.cerrarModales();
        },
        error: (err) => alert("❌ Error en la actualización.")
      });
  }

  cargarListaGrupos() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-equipos`, { headers: this.getAuthHeaders() })
      .subscribe(res => this.listaEquipos = res);
  }

  cargarRadicados() {
    this.http.get<any[]>(`${this.apiUrl}/radicados`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.listaRadicados = res;
          setTimeout(() => this.cd.detectChanges(), 0);
        },
        error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudieron cargar los radicados.', 'error')
      });
  }

  cargarUsuariosActivos() {
    this.http.get<any[]>(`${this.apiUrl}/usuarios-activos`, { headers: this.getAuthHeaders() })
      .subscribe({ next: (res) => { this.usuariosActivos = res; } });
  }

  cargarNotificaciones() {
    this.http.get<any[]>(`${this.apiUrl}/mis-notificaciones`, { headers: this.getAuthHeaders() })
      .subscribe({ next: (res) => { this.notificaciones = res; this.cd.detectChanges(); } });
  }

  get notificacionesSinLeer(): number {
    return this.notificaciones.filter(n => !n.leida).length;
  }

  marcarLeida(id: number) {
    this.http.post(`${this.apiUrl}/mis-notificaciones/${id}/leer`, {}, { headers: this.getAuthHeaders() })
      .subscribe({ next: () => {
        const n = this.notificaciones.find(n => n.id === id);
        if (n) { n.leida = 1; this.cd.detectChanges(); }
      }});
  }

  abrirModalTraslado(radicado: any) {
    this.radicadoSeleccionado = radicado;
    this.trasladoNuevoResponsableId = null;
    this.trasladoComentario = '';
    this.mostrarModalTraslado = true;
    this.cd.detectChanges();
  }

  ejecutarTraslado() {
    if (!this.trasladoNuevoResponsableId) {
      Swal.fire('Atención', 'Debes seleccionar un funcionario destino.', 'warning'); return;
    }
    this.http.post(`${this.apiUrl}/radicados/${encodeURIComponent(this.radicadoSeleccionado.nro_radicado)}/trasladar`,
      { nuevo_responsable_id: this.trasladoNuevoResponsableId, comentario: this.trasladoComentario },
      { headers: this.getAuthHeaders() }
    ).subscribe({
      next: (res: any) => {
        this.mostrarModalTraslado = false;
        Swal.fire('✅ Traslado realizado', res.mensaje, 'success');
        this.cargarRadicados();
      },
      error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudo realizar el traslado.', 'error')
    });
  }

  abrirHistorial(radicado: any) {
    this.radicadoSeleccionado = radicado;
    this.historialActual = [];
    this.cargandoHistorial = true;
    this.mostrarModalHistorial = true;
    this.http.get<any[]>(`${this.apiUrl}/radicados/${encodeURIComponent(radicado.nro_radicado)}/historial`,
      { headers: this.getAuthHeaders() }
    ).subscribe({
      next: (res) => { this.historialActual = res; this.cargandoHistorial = false; this.cd.detectChanges(); },
      error: () => { this.cargandoHistorial = false; this.cd.detectChanges(); Swal.fire('Error', 'No se pudo cargar el historial.', 'error'); }
    });
  }

  ejecutarArchivar(radicado: any) {
    Swal.fire({
      title: `¿Archivar ${radicado.nro_radicado}?`,
      text: 'Esto finaliza el ciclo del documento. Puedes agregar un comentario.',
      input: 'textarea',
      inputPlaceholder: 'Comentario de cierre...',
      showCancelButton: true,
      confirmButtonText: '📦 Archivar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#475569'
    }).then(result => {
      if (result.isConfirmed) {
        this.http.post(`${this.apiUrl}/radicados/${encodeURIComponent(radicado.nro_radicado)}/archivar`,
          { comentario: result.value || 'Archivado.' },
          { headers: this.getAuthHeaders() }
        ).subscribe({
          next: () => { Swal.fire('Archivado', 'El radicado fue finalizado.', 'success'); this.cargarRadicados(); },
          error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudo archivar.', 'error')
        });
      }
    });
  }

  buscarArchivoCentral() {
    const { q, anio, serie, caja, disposicion } = this.filtrosArchivo;
    const params: any = {};
    if (q) params['q'] = q;
    if (anio) params['anio'] = anio;
    if (serie) params['serie'] = serie;
    if (caja) params['caja'] = caja;
    if (disposicion) params['disposicion'] = disposicion;
    this.http.get<any[]>(`${this.apiUrl}/archivo-central`, { headers: this.getAuthHeaders(), params })
      .subscribe({
        next: (res) => { this.listaArchivoCentral = res; this.cd.detectChanges(); },
        error: (err) => Swal.fire('Error', err.error?.detail || 'Error al consultar el archivo.', 'error')
      });
  }

  limpiarFiltrosArchivo() {
    this.filtrosArchivo = { q: '', anio: 0, serie: '', caja: '', disposicion: '' };
    this.buscarArchivoCentral();
  }

  abrirModalTransferencia(radicado: any) {
    this.radicadoATransferir = radicado;
    this.transferenciaData = { caja: '', carpeta: '', folio_inicio: null, folio_fin: null, llaves_busqueda: '', observaciones: '' };
    this.mostrarModalTransferencia = true;
    this.cd.detectChanges();
  }

  ejecutarTransferencia() {
    if (!this.transferenciaData.caja || !this.transferenciaData.carpeta) {
      Swal.fire('Atención', 'Caja y Carpeta son obligatorias para la transferencia.', 'warning'); return;
    }
    this.http.post(
      `${this.apiUrl}/radicados/${encodeURIComponent(this.radicadoATransferir.nro_radicado)}/transferir-archivo`,
      this.transferenciaData,
      { headers: this.getAuthHeaders() }
    ).subscribe({
      next: (res: any) => {
        this.mostrarModalTransferencia = false;
        Swal.fire('📦 Transferido', res.mensaje, 'success');
        this.cargarRadicados();
      },
      error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudo transferir.', 'error')
    });
  }

  resaltarRadicado(nroRadicado: string) {
    this.busquedaRadicados = nroRadicado;
    this.cd.detectChanges();
    // Scroll suave al top de la tabla
    setTimeout(() => {
      const el = document.querySelector('.siade-table');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }

  verDocumentoRadicado(nroRadicado: string) {
    const url = `${this.apiUrl}/radicados/${encodeURIComponent(nroRadicado)}/documento`;
    const token = localStorage.getItem('token') || '';
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        if (!res.ok) throw new Error('Documento no disponible');
        return res.blob();
      })
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, '_blank');
      })
      .catch(() => Swal.fire('Sin documento', 'No se encontró el archivo adjunto para este radicado.', 'info'));
  }

  get radicadosFiltrados(): any[] {
    const hoy = new Date().toISOString().split('T')[0];
    return this.listaRadicados.filter(r => {
      const q = this.busquedaRadicados.toLowerCase();
      if (q && !(
        r.nro_radicado?.toLowerCase().includes(q) ||
        r.nombre_razon_social?.toLowerCase().includes(q) ||
        r.asunto?.toLowerCase().includes(q) ||
        r.serie?.toLowerCase().includes(q) ||
        r.responsable_nombre?.toLowerCase().includes(q)
      )) return false;
      if (this.filtrosGestion.tipo && r.tipo_radicado !== this.filtrosGestion.tipo) return false;
      if (this.filtrosGestion.estado && r.estado !== this.filtrosGestion.estado) return false;
      if (this.filtrosGestion.serie && !r.serie?.toLowerCase().includes(this.filtrosGestion.serie.toLowerCase())) return false;
      if (this.filtrosGestion.vencido === 'si' && !(r.fecha_vencimiento && r.fecha_vencimiento < hoy)) return false;
      if (this.filtrosGestion.vencido === 'no' && (r.fecha_vencimiento && r.fecha_vencimiento < hoy)) return false;
      return true;
    });
  }

  limpiarFiltrosGestion() {
    this.busquedaRadicados = '';
    this.filtrosGestion = { tipo: '', estado: '', serie: '', vencido: '' };
    this.cd.detectChanges();
  }

  // --- LÓGICA DE CARGA MASIVA Y PLANTILLAS ---

  descargarPlantilla(tipo: string) {
    // Apunta a la carpeta static/templates de tu FastAPI
    const url = `${this.apiUrl}/admin/descargar-plantilla-trd`;

    Swal.fire({
      title: 'Descargando...',
      text: 'Estamos preparando tu plantilla oficial de TRD.',
      icon: 'info',
      timer: 2000,
      showConfirmButton: false,
      toast: true,
      position: 'top-end'
    });
    
    console.log(`Solicitando descarga de plantilla para: ${tipo}`);
    window.open(url, "_blank");
  }

  abrirSelectorArchivo(tipo: string) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx, .xls';
    
    input.onchange = (e: any) => {
      const archivo = e.target.files[0];
      if (archivo) {
        this.subirExcel(archivo, tipo);
      }
    };
    
    input.click();
  }

  subirExcel(archivo: File, tipo: string) {
    const formData = new FormData();
    formData.append('file', archivo);

    const endpoint = tipo === 'trd' ? '/admin/importar-trd-excel' : '/admin/importar-estructura-excel';

    this.http.post(`${this.apiUrl}${endpoint}`, formData, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res: any) => {
          // --- POP-UP DE ÉXITO ---
          Swal.fire({
            title: '¡Importación Exitosa!',
            text: `Se han procesado ${res.count} registros masivamente en la base de datos Alfa.`,
            icon: 'success',
            confirmButtonText: 'Entendido',
            confirmButtonColor: '#7c3aed', // Color morado que usas en tu tema
          }).then((result) => {
            // Recarga automática según la sección
            if (tipo === 'trd') this.cargarTRD();
            else this.cargarEstructura();
            
            // Si quieres que después del éxito lo mande a la vista principal del dashboard:
            // this.seccionActiva = 'dashboard';
            
            this.cd.detectChanges();
          });
        },
        error: (err) => {
          // --- POP-UP DE ERROR ---
          Swal.fire({
            title: 'Error de Formato',
            text: err.error?.detail || 'El archivo Excel no coincide con la plantilla oficial.',
            icon: 'error',
            confirmButtonText: 'Revisar Plantilla',
            confirmButtonColor: '#f43f5e'
          });
        }
      });
  }

  // --- LÓGICA DE MODALES ---

  abrirConfiguracion() {
    this.mostrarModalConfig = true;
    this.cd.detectChanges(); 
  }

  cambiarPassword() {
    alert("Funcionalidad de cambio de contraseña en desarrollo.");
  }

  abrirModalCrear() {
    this.mostrarFormularioCrear = true;
  }

  abrirModalUsuarios() {
    this.mostrarModalUsuarios = true;
    this.cargarUsuarios(); 
  }

  cerrarModales() {
    this.mostrarFormularioCrear = false;
    this.mostrarModalUsuarios = false;
    this.mostrarModalConfig = false;
    this.mostrarModalCrearGrupo = false;
    this.mostrarModalAsignarGrupo = false; 
    this.usuarioSeleccionado = null;
    this.nombreNuevoGrupo = '';
    this.mostrarModalCrearGrupo = false;
    this.pasoCreacionGrupo = 1; // <--- VOLVEMOS AL PASO 1 PARA LA PRÓXIMA VEZ
    this.nombreNuevoGrupo = '';
  }

  // --- GESTIÓN DE DATOS ---

  cargarUsuarios() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-usuarios`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          this.listaUsuarios = res;
          this.cd.detectChanges(); 
        },
        error: (err) => {
          if (err.status === 403) alert('Se requieren permisos de Administrador.');
        }
      });
  }

  // --- AJUSTE: CONTROL DE ACCESO (SOFT DELETE) ---
  toggleEstadoUsuario(user: any) {
    const accion = user.activo ? 'DESACTIVAR' : 'ACTIVAR';
    const confirmacion = confirm(`¿Desea ${accion} el acceso de ${user.nombre_completo} al sistema?`);
    
    if (confirmacion) {
      const payload = {
        user_id: user.id,
        nuevo_estado: !user.activo
      };

      console.log(`%c--- SOLICITANDO CAMBIO DE ESTADO (ID: ${user.id}) ---`, "color: #f43f5e; font-weight: bold;");

      this.http.post(`${this.apiUrl}/admin/cambiar-estado-usuario`, payload, { headers: this.getAuthHeaders() })
        .subscribe({
          next: (res: any) => {
            user.activo = !user.activo;
            this.cd.detectChanges();
          },
          error: (err) => {
            alert("❌ Error: " + (err.error?.detail || "Fallo al comunicar con el servidor"));
          }
        });
    }
  }

  iniciarMonitoreo() {
    this.obtenerEventos();
    this.auditSubscription = interval(10000).subscribe(() => {
      this.obtenerEventos();
    });
  }

  obtenerEventos() {
    this.http.get<any[]>(`${this.apiUrl}/admin/eventos-recientes`, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => this.eventosRecientes = res,
        error: (err) => console.error('Error en feed de auditoría', err)
      });
  }

  // ----- SERIES Y SUBSERIES CREADAS POR TRD
  getSeriesUnicas() {
    if (!this.listaTRD || this.listaTRD.length === 0) return [];
    const seriesMap = new Map();
    this.listaTRD.forEach(item => {
      const nom = (item.serie || '').toString().trim();
      const cod = (item.codigo || '').toString().trim();
      if (nom) seriesMap.set(nom, `${cod} - ${nom}`);
    });
    return Array.from(seriesMap.entries()).map(([nombre, etiqueta]) => ({ nombre, etiqueta }));
  }

  getSubseriesUnicas() {
    if (!this.radicado.serie || !this.listaTRD) return [];
    const subseriesMap = new Map();
    this.listaTRD
      .filter(item => (item.serie || '').toString() === this.radicado.serie.toString())
      .forEach(item => {
        const nom = (item.subserie || '').toString().trim();
        const cod = (item.cod_subserie || '').toString().trim(); // ¡Ya existe!
        if (nom) {
          const etiqueta = cod ? `${cod} - ${nom}` : nom;
          subseriesMap.set(nom, etiqueta);
        }
      });
    return Array.from(subseriesMap.entries()).map(([nombre, etiqueta]) => ({ nombre, etiqueta }));
  }

  getTiposDocumentalesUnicos() {
    if (!this.radicado.serie || !this.listaTRD) return [];
    const tipos = this.listaTRD
      .filter(item => (item.serie || '').toString() === this.radicado.serie.toString())
      .map(item => (item.tipo_documental || '').toString().trim()); // ¡Ya existe!
      
    return [...new Set(tipos)].filter(t => t !== '');
  }

      // --- ACCIONES SIADE ---

  generarRadicadoOficial() {
    const formData = new FormData();
    
    // 1. Datos básicos
    formData.append('tipo', this.obtenerPrefijo()); 
    formData.append('asunto', this.radicado.asunto || `Radicación - ${new Date().toLocaleDateString()}`);
    formData.append('remitente', this.userName);

    // 2. La TRD
    formData.append('serie', this.radicado.serie); 
    formData.append('subserie', this.radicado.subserie);
    formData.append('tipo_documental', this.radicado.tipoDocumental);

    // 3. El Responsable (Usamos tu variable: funcionarioResponsable)
    formData.append('responsable', this.radicado.funcionarioResponsable || 'Juan Perez - Ventanilla');

    // 4. El Archivo (Usamos tu variable: archivoBinarioPrincipal)
    if (this.archivoBinarioPrincipal) {
      formData.append('archivo', this.archivoBinarioPrincipal);
    } else {
      Swal.fire('Atención', 'Debe adjuntar el documento principal.', 'warning');
      return;
    }

    // 5. El campo "con_copia" (Arreglo para el error de Pydantic de la imagen)
    // El servidor espera un string, le mandamos el array como JSON string
    formData.append('con_copia', JSON.stringify(this.radicado.conCopia || []));

    this.http.post<any>(`${this.apiUrl}/radicar`, formData, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res) => {
          Swal.fire('✅ ÉXITO', `Radicado ${res.numero} generado.`, 'success');
          this.obtenerEventos(); 
          this.limpiarFormularioRadicacion(); // Usamos tu nombre de función real
        },
        error: (err) => {
          console.error('Error:', err);
          Swal.fire('❌ Error', err.error?.detail || 'Fallo de servidor', 'error');
        }
      });
  }

  crearUsuario() {
    const formData = new FormData();
    formData.append('usuario_nuevo', this.nuevoUser.usuario);
    formData.append('password_nueva', this.nuevoUser.password);
    formData.append('nombre_completo', this.nuevoUser.nombre);
    formData.append('rol_id', this.nuevoUser.rol_id.toString());

    this.http.post(`${this.apiUrl}/admin/crear-usuario`, formData, { headers: this.getAuthHeaders() })
      .subscribe({
        next: (res: any) => {
          alert(`Usuario registrado.\nSecreto 2FA: ${res.secret_2fa}`);
          this.cerrarModales();
          this.nuevoUser = { nombre: '', usuario: '', password: '', rol_id: 3 };
          this.obtenerEventos(); 
        },
        error: (err) => alert('Error al crear: ' + (err.error?.detail || 'Fallo de red'))
      });
  }

    // Función para manejar la selección de archivos
  onFileSelected(event: any, tipo: string) {
    const archivo = event.target.files[0];
    if (archivo) {
      if (tipo === 'principal') {
        this.nombreArchivoPrincipal = archivo.name;
        this.archivoBinarioPrincipal = archivo;
        console.log("Documento principal cargado:", archivo.name);
      } else {
        this.nombreArchivoAnexo = `${event.target.files.length} archivo(s) seleccionado(s)`;
        this.anexosBinarios = Array.from(event.target.files);
        console.log("Anexos cargados:", event.target.files.length);
      }
      this.cd.detectChanges();
    }
  }

  getRoleName(rolId: number): string {
    const roles: { [key: number]: string } = {
      0: 'Super Administrador',
      1: 'Administrador',
      2: 'Archivista (TRD)',
      3: 'Radicador',
      4: 'Consultor'
    };
    return roles[rolId] || 'Funcionario SIADE';
  }

  cerrarSesion() {
    localStorage.removeItem('token');
    this.router.navigate(['/login']);
  }

  obtenerPrefijo(): string {
    const mapeo: { [key: string]: string } = {
      'recibidas': 'RAD',
      'enviadas': 'ENV',
      'internas': 'INV',
      'no-radicables': 'NOR'
    };
    
    // Retorna el prefijo según la pestaña activa o 'RAD' por defecto
    return mapeo[this.tabActivaVentanilla] || 'RAD';
  }

  ngOnDestroy() {
    if (this.auditSubscription) {
      this.auditSubscription.unsubscribe();
    }
  }
}
