import { Component, OnInit, OnDestroy, AfterViewInit, ChangeDetectorRef, ViewChild, ElementRef } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FlujosBpmnComponent } from '../flujos/flujos';
import BpmnViewer from 'bpmn-js';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { jwtDecode } from 'jwt-decode';
import { interval, Subscription } from 'rxjs';
import Swal from 'sweetalert2';
import { jsPDF } from 'jspdf';
import QRCode from 'qrcode';
import { Chart, registerables } from 'chart.js';
import * as XLSX from 'xlsx';
import { environment } from '../../../environments/environment';
import { COLOMBIA_DEPARTAMENTOS, COLOMBIA_DEPARTAMENTOS_MUNICIPIOS } from '../../data/colombia-municipios';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
  standalone: false
})
export class Dashboard implements OnInit, AfterViewInit, OnDestroy {
  // --- DATOS GEOGRÁFICOS COLOMBIA ---
  readonly departamentos = COLOMBIA_DEPARTAMENTOS;
  municipios: string[] = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS['Caldas'] ?? [];
  municipiosEnviada: string[] = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS['Caldas'] ?? [];

  onDepartamentoChange(): void {
    this.municipios = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS[this.radicado.departamento] ?? [];
    this.radicado.ciudad = this.municipios[0] ?? '';
  }

  onDepartamentoEnviadaChange(): void {
    this.municipiosEnviada = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS[this.radicado.departamento] ?? [];
    this.radicado.ciudad = this.municipiosEnviada[0] ?? '';
  }

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
  qrPreviewUrl: string = ''; // URL del QR en tiempo real

  // --- VALIDACIÓN DE FORMULARIO DE RADICACIÓN ---
  formSubmitted: boolean = false;
  erroresForm: {[key: string]: string} = {};

  // --- VARIABLES PARA ADJUNTOS ---
nombreArchivoPrincipal: string = '';
nombreArchivoAnexo: string = '';
archivoBinarioPrincipal: File | null = null;
anexosBinarios: File[] = [];

  // --- CONFIGURACIÓN DEL MENÚ DINÁMICO ---
  menuItems = [
    { label: 'Dashboard',          icon: '📈', roles: [0, 1, 2, 3] },
    { label: 'Buzón',              icon: '📬', roles: [0, 1, 2] },
    { label: 'Flujos de Trabajo',  icon: '🌿', roles: [0, 1] },
    { label: 'Ventanilla Única',   icon: '📥', roles: [0, 1, 2] },
    { label: 'Archivo Central',    icon: '📦', roles: [0, 1] },
    { label: 'Archivo Histórico',  icon: '🏛️', roles: [0, 1] },
    { label: 'Informes',           icon: '📊', roles: [0, 1] },
    { label: 'Configuración',      icon: '⚙️', roles: [0, 1] }
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
        // Re-inicializar gráficas: *ngIf recrea los canvas al volver al dashboard
        setTimeout(() => this.cargarGraficas(), 100);
        break;

      case 'Configuración':
        this.seccionActiva = 'configuracion';
        this.tabActivaConfig = 'estructura-organica'; // Tab inicial por defecto
        break;

      case 'Ventanilla Única':
        this.seccionActiva = 'ventanilla';
        this.tabActivaVentanilla = 'recibidas';
        break;

      case 'Buzón':
        this.seccionActiva = 'gestion-documental';
        this.cargarRadicados();
        break;

      case 'Archivo Central':
        this.seccionActiva = 'archivo-central';
        this.buscarArchivoCentral();
        break;

      case 'Flujos de Trabajo':
        this.seccionActiva = 'flujos';
        this.flujoTab = 'ver';
        break;

      case 'Informes':
        this.seccionActiva = 'informes';
        this.cargarInformes();
        break;

      default:
        alert(`La sección de ${label} está en desarrollo.`);
        break;
    }

    // 3. Forzamos la detección de cambios para actualizar la interfaz
    setTimeout(() => this.cd.detectChanges(), 0);
  }

  // Función para cambiar pestañas de ventanilla
  cambiarTabVentanilla(tab: string) {
    this.tabActivaVentanilla = tab;
    this.formSubmitted = false;
    this.erroresForm = {};
    this.cd.detectChanges();
  }

  // --- BUZÓN ---
  cambiarTabBuzon(tab: string) {
    this.tabBuzon = tab;
    this.filtroOrganizarBuzon = '';
    this.textoBuzonFiltro = '';
    this.fechaInicioBuzon = '';
    this.fechaFinBuzon = '';
    this.mostrarSugerenciasBuzon = false;
  }

  cambiarFiltroBuzon(filtro: string) {
    this.filtroOrganizarBuzon = this.filtroOrganizarBuzon === filtro ? '' : filtro;
    this.textoBuzonFiltro = '';
    this.fechaInicioBuzon = '';
    this.fechaFinBuzon = '';
    this.mostrarSugerenciasBuzon = false;
  }

  getSugerenciasBuzon(): string[] {
    if (!this.textoBuzonFiltro.trim()) return [];
    const q = this.textoBuzonFiltro.toLowerCase();
    let valores: string[] = [];
    const lista = this.radicadosFiltrados || [];
    switch (this.filtroOrganizarBuzon) {
      case 'radicado':    valores = lista.map((r: any) => r.nro_radicado); break;
      case 'serie':       valores = lista.map((r: any) => r.serie); break;
      case 'remitente':   valores = lista.map((r: any) => r.nombre_razon_social); break;
      case 'destinatario':valores = lista.map((r: any) => r.destinatario); break;
      case 'asunto':      valores = lista.map((r: any) => r.asunto); break;
    }
    return [...new Set(valores)].filter((v: any) => v && v.toLowerCase().includes(q)).slice(0, 8) as string[];
  }

  seleccionarSugerenciaBuzon(val: string) {
    this.textoBuzonFiltro = val;
    this.mostrarSugerenciasBuzon = false;
  }

  getBuzonFiltrado(): any[] {
    let lista: any[] = this.radicadosFiltrados || [];
    // Filtrar por tab
    if (this.tabBuzon === 'recibidos') {
      lista = lista.filter((r: any) => r.tipo_radicado === 'RECIBIDA' || r.tipo_radicado === 'RECIBIDAS');
    } else if (this.tabBuzon === 'enviados') {
      lista = lista.filter((r: any) => r.tipo_radicado === 'ENVIADA' || r.tipo_radicado === 'ENVIADAS');
    }
    // Filtrar por rango de fecha
    if (this.filtroOrganizarBuzon === 'fecha') {
      if (this.fechaInicioBuzon) lista = lista.filter((r: any) => r.fecha_radicado >= this.fechaInicioBuzon);
      if (this.fechaFinBuzon)    lista = lista.filter((r: any) => r.fecha_radicado <= this.fechaFinBuzon);
    }
    // Filtrar por texto
    if (this.filtroOrganizarBuzon !== 'fecha' && this.textoBuzonFiltro.trim()) {
      const q = this.textoBuzonFiltro.toLowerCase();
      switch (this.filtroOrganizarBuzon) {
        case 'radicado':    lista = lista.filter((r: any) => r.nro_radicado?.toLowerCase().includes(q)); break;
        case 'serie':       lista = lista.filter((r: any) => r.serie?.toLowerCase().includes(q)); break;
        case 'remitente':   lista = lista.filter((r: any) => r.nombre_razon_social?.toLowerCase().includes(q)); break;
        case 'destinatario':lista = lista.filter((r: any) => r.destinatario?.toLowerCase().includes(q)); break;
        case 'asunto':      lista = lista.filter((r: any) => r.asunto?.toLowerCase().includes(q)); break;
      }
    }
    return lista;
  }

  abrirAccionesBuzon(r: any) {
    this.radicadoBuzonAcciones = r;
    this.mostrarPopupAccionesBuzon = true;
  }

  cerrarAccionesBuzon() {
    this.mostrarPopupAccionesBuzon = false;
    this.radicadoBuzonAcciones = null;
  }

  abrirInfoBuzon(r: any) {
    this.radicadoInfoBuzon = r;
    this.tabInfoBuzon = 'informacion';
    this.historialActual = [];
    this.mostrarPopupInfoBuzon = true;
  }

  cerrarInfoBuzon() {
    this.mostrarPopupInfoBuzon = false;
    this.radicadoInfoBuzon = null;
  }

  cambiarTabInfoBuzon(tab: string) {
    this.tabInfoBuzon = tab;
    if (tab === 'recorrido' && this.radicadoInfoBuzon && this.historialActual.length === 0) {
      this.cargandoHistorial = true;
      this.http.get<any[]>(`${this.apiUrl}/radicados/${encodeURIComponent(this.radicadoInfoBuzon.nro_radicado)}/historial`)
        .subscribe({
          next: (res) => { this.historialActual = res; this.cargandoHistorial = false; this.cd.detectChanges(); },
          error: () => { this.cargandoHistorial = false; this.cd.detectChanges(); }
        });
    }
    if (tab === 'responder') {
      this.inicializarRespuesta();
    }
  }

  inicializarRespuesta() {
    const r = this.radicadoInfoBuzon;
    this.respuestaForm = {
      tipoDocumento:       'Externo',
      tipoDestinatario:    'Natural',
      primerApellido:      '',
      segundoApellido:     '',
      nombreDestinatario:  r?.nombre_razon_social || '',
      tipoDocDestinatario: r?.tipo_doc_remitente  || 'Cédula de Ciudadanía',
      nroDocDestinatario:  r?.nro_doc_remitente   || '',
      cargo:               r?.cargo               || '',
      direccion:           r?.direccion           || '',
      telefono:            r?.telefono            || '',
      correo:              r?.correo              || '',
      pais:                r?.pais                || 'Colombia',
      departamento:        r?.departamento        || 'Caldas',
      ciudad:              r?.ciudad              || 'Manizales',
      serie:               '',
      subserie:            '',
      tipoDocumental:      '',
      asunto:              r?.asunto ? `RE: ${r.asunto}` : '',
      metodoEnvio:         'Físico',
      nroGuia:             '',
      nroFolios:           '',
      anexo:               '',
      descripcionAnexo:    '',
      activaFlujo:         false,
    };
    this.municipiosRespuesta = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS[this.respuestaForm.departamento] ?? [];
    this.nombreArchivoPrincipalRespuesta = '';
    this.nombreArchivoAnexoRespuesta     = '';
    this.archivoBinarioPrincipalRespuesta = null;
    this.archivoBinarioAnexoRespuesta     = null;
    this.mostrarFormDestinatarioAdicional = false;
  }

  onDepartamentoRespuestaChange() {
    this.municipiosRespuesta = COLOMBIA_DEPARTAMENTOS_MUNICIPIOS[this.respuestaForm.departamento] ?? [];
    this.respuestaForm.ciudad = this.municipiosRespuesta[0] ?? '';
  }

  onFileRespuestaSelected(event: any, tipo: string) {
    const file = event.target.files[0];
    if (!file) return;
    if (tipo === 'principal') {
      this.archivoBinarioPrincipalRespuesta = file;
      this.nombreArchivoPrincipalRespuesta  = file.name;
    } else {
      this.archivoBinarioAnexoRespuesta = file;
      this.nombreArchivoAnexoRespuesta  = file.name;
    }
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
      permisos: ['Carga/Descarga de Tablas de Configuración', 'Gestión de Sedes, Unidades y Oficinas', 'Administración de TRD (Series/Subseries)', 'Diseño de flujos y anulación de registros'],
      hereda: 'Usuario Productor'
    },
    {
      nombre: 'Usuario Productor',
      nivel: 'Nivel 2',
      color: '#d97706',
      permisos: ['Radicar comunicaciones', 'Aprobar y Trasladar documentos', 'Remitir y Archivar correspondencia', 'Devolver e Imprimir registros oficiales'],
      hereda: 'Usuario Consultor'
    },
    {
      nombre: 'Usuario Consultor',
      nivel: 'Nivel 3',
      color: '#64748b',
      permisos: ['Búsqueda y consulta de documentos', 'Visualización de expedientes públicos', 'Generación de reportes básicos'],
      hereda: null
    }
  ];

  // --- ESTRUCTURA ORGÁNICA (Niveles 1 y 2) ---
  entidadInfo = {
    nombre: 'Alcaldía de Manizales',
    fondoSeleccionado: 'Gestión Administrativa',
    fondosDisponibles: ['Gestión Administrativa', 'Archivo Central', 'Académico'],
    sedes: ''
  };

  sedesDisponibles: string[] = ['SEDE 1', 'SEDE 2', 'SEDE 3', 'SEDE 4', 'SEDE 5'];
  sedesSeleccionadas: string[] = [];
  mostrarDropdownSedes: boolean = false;

  toggleSede(sede: string) {
    const idx = this.sedesSeleccionadas.indexOf(sede);
    if (idx >= 0) {
      this.sedesSeleccionadas.splice(idx, 1);
    } else {
      this.sedesSeleccionadas.push(sede);
    }
    this.entidadInfo.sedes = this.sedesSeleccionadas.join(', ');
  }

  isSedeSeleccionada(sede: string): boolean {
    return this.sedesSeleccionadas.includes(sede);
  }

  nuevaDependencia = {
    codUnidad: '',
    unidadNombre: '',
    codOficina: '',
    oficinaNombre: ''
  };
  mostrarModalDependencia: boolean = false;

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

  listaTRD: any[] = [];
  catalogoSeries: any[] = [];
  catalogoSubseries: any[] = [];       // Para dropdowns de ventanilla (filtrado al seleccionar serie)
  catalogoSubseriesTRD: any[] = [];    // Para dropdowns del formulario TRD
  
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
  paginacionRadicados = { page: 1, per_page: 50, total: 0, total_pages: 1 };

  // --- BUZÓN ---
  tabBuzon: string = 'recibidos';
  filtroOrganizarBuzon: string = '';
  textoBuzonFiltro: string = '';
  fechaInicioBuzon: string = '';
  fechaFinBuzon: string = '';
  mostrarSugerenciasBuzon: boolean = false;
  mostrarPopupAccionesBuzon: boolean = false;
  radicadoBuzonAcciones: any = null;
  // Popup información del documento
  mostrarPopupInfoBuzon: boolean = false;
  radicadoInfoBuzon: any = null;
  tabInfoBuzon: string = 'informacion';

  // --- RESPONDER EN BUZÓN ---
  respuestaForm: any = {};
  municipiosRespuesta: string[] = [];
  nombreArchivoPrincipalRespuesta: string = '';
  nombreArchivoAnexoRespuesta: string = '';
  archivoBinarioPrincipalRespuesta: File | null = null;
  archivoBinarioAnexoRespuesta: File | null = null;
  mostrarFormDestinatarioAdicional: boolean = false;
  // --- ARCHIVO CENTRAL ---
  listaArchivoCentral: any[] = [];
  filtrosArchivo = { q: '', anio: 0, serie: '', caja: '', disposicion: '' };
  mostrarModalTransferencia: boolean = false;
  radicadoATransferir: any = null;
  transferenciaData = { caja: '', carpeta: '', folio_inicio: null as number|null, folio_fin: null as number|null, llaves_busqueda: '', observaciones: '' };
  usuariosActivos: any[] = [];
  notificaciones: any[] = [];
  // --- KPIs DASHBOARD ---
  kpi: any = {
    volumen:       { hoy: 0, ayer: 0, variacion_pct: 0 },
    ans:           { pct: 0, vencen_hoy: 0 },
    eficiencia:    { pct: 0, en_tramite: 0 },
    archivo:       { total: 0, mes: 0, pct_mes: 0 },
    ans_breakdown: {
      cumplimiento:   { pct: 0, count: 0 },
      en_riesgo:      { pct: 0, count: 0 },
      incumplimiento: { pct: 0, count: 0 }
    },
    ultimas: []
  };
  mesActual: string = new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
  // --- MODALES FLUJO ---
  // --- AUDITORÍA ---
  listaAuditLogs: any[] = [];
  filtrosAudit = { usuario: '', modulo: '', fecha_desde: '', fecha_hasta: '' };
  auditPaginacion = { page: 1, per_page: 50, total: 0, total_pages: 1 };
  mostrarModalTraslado: boolean = false;
  mostrarModalHistorial: boolean = false;
  flujoTab: 'ver' | 'editar' = 'ver';  // T8.2: tabs del visualizador/editor BPMN
  mostrarModalFlujo: boolean = false;
  cargandoFlujo: boolean = false;
  radicadoFlujoActual: any = null;
  flujoTieneInstancia: boolean = false;
  pasoActualFlujo: string = '';
  private bpmnModalViewer: any = null;

  // --- FACTURAS DIAN (T4.5.1 / T4.5.2) ---
  facturasDianLista: any[] = [];
  busquedaFacturasDian: string = '';
  mostrarModalPreviewDian: boolean = false;
  mostrarModalDetalleDian: boolean = false;
  previewDianData: any = null;
  facturaDianDetalle: any = null;
  archivoDianSeleccionado: File | null = null;
  cargandoRadicacionDian: boolean = false;

  // --- PDF SPLITTING (T4.4.3) ---
  mostrarModalDividirPdf: boolean = false;
  infoPdf: any = null;
  cargandoInfoPdf: boolean = false;
  radicadoPdfActual: any = null;
  pdfPaginaInicio: number = 1;
  pdfPaginaFin: number = 1;

  @ViewChild('bpmnModalContainer') bpmnModalContainer: any;
  @ViewChild('chartBarras') chartBarrasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartDona') chartDonaRef!: ElementRef<HTMLCanvasElement>;
  private chartBarras: Chart | null = null;
  private chartDona: Chart | null = null;
  graficasListas: boolean = false;

  // --- INFORMES ---
  @ViewChild('chartLinea') chartLineaRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') chartTipoRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartAnsDep') chartAnsDepRef!: ElementRef<HTMLCanvasElement>;
  private chartLinea: Chart | null = null;
  private chartTipoPie: Chart | null = null;
  private chartAnsDep: Chart | null = null;
  informesListas: boolean = false;
  informesCargando: boolean = false;
  filtrosInformes = { fecha_desde: '', fecha_hasta: '', tipo: '', dependencia: '' };
  informesResumen: any[] = [];
  informesPeriodo: string = '';
  cargandoHistorial: boolean = false;
  mostrarModalCambioPassword: boolean = false;
  esCambioForzado: boolean = false;
  formCambioPassword = { password_actual: '', password_nuevo: '', password_confirmar: '' };
  errorCambioPassword: string = '';
  radicadoSeleccionado: any = null;
  historialActual: any[] = [];
  trasladoNuevoResponsableId: number | null = null;
  trasladoComentario: string = '';
  archivarComentario: string = '';
  
 // --- [AJUSTADO] ALMACENAMIENTO PARA GRUPOS ---
  listaEquipos: any[] = []; // Listado de grupos para los checkboxes
  userParaAsignar: any = null;

  private auditSubscription?: Subscription;
  private relojInterval?: ReturnType<typeof setInterval>;

  nuevoUser = {
    nombre: '',
    usuario: '',
    rol_id: 3
  };

  private apiUrl = environment.apiUrl;

  // --- VISOR PDF ---
  mostrarModalPdf: boolean = false;
  pdfUrlSegura: SafeResourceUrl | null = null;
  pdfNroRadicado: string = '';
  private _pdfBlobUrl: string = '';

  constructor(
    private router: Router,
    private http: HttpClient,
    private cd: ChangeDetectorRef,
    private sanitizer: DomSanitizer
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

        // Reloj en tiempo real para la fecha de radicación
        const actualizarReloj = () => {
          this.fechaActualRadicado = new Date().toLocaleString('es-CO', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
          });
        };
        actualizarReloj();
        this.relojInterval = setInterval(actualizarReloj, 1000);

        // Inicializar fecha de vencimiento según días hábiles por defecto (15)
        this.radicado.fechaVencimiento = this.calcularFechaVencimiento(this.radicado.diasRespuesta);

        // Generar QR de previsualización inicial
        this.actualizarQRPreview();

        // Carga inicial de datos persistentes
        this.cargarEstructura();
        this.cargarTRD();
        this.cargarCatalogoSeries();
        this.cargarListaGrupos();
        this.cargarUsuariosActivos();
        this.cargarNotificaciones();
        this.cargarKpis();
        this.cargarGraficas();

        if (this.userRole <= 1) {
          this.iniciarMonitoreo();
        }

        // Verificar si el usuario debe cambiar su contraseña
        if (localStorage.getItem('debe_cambiar_password') === '1') {
          this.esCambioForzado = true;
          this.formCambioPassword = { password_actual: '', password_nuevo: '', password_confirmar: '' };
          this.errorCambioPassword = '';
          this.mostrarModalCambioPassword = true;
          this.cd.detectChanges();
        }

      } catch (error) {
        this.cerrarSesion();
      }
    } else {
      this.router.navigate(['/login']);
    }
  }

  
  // Headers manejados automáticamente por AuthInterceptor (T5.1.2)

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
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-estructura`)
      .subscribe({
        next: (res) => {
          this.unidadesOrganicas = res;
          this.unidadesDisponibles = [...new Set(res.map((u: any) => u.unidad))];
          this.cd.detectChanges();
        },
        error: () => console.warn("Modo local: No se pudo cargar la estructura.")
      });
  }

  // ── Códigos para tabla de estructura orgánica (vienen directo de la BD) ──────
  getCodUnidad(u: any): string { return u.cod_unidad || '--'; }
  getCodOficina(u: any): string { return u.cod_oficina || ''; }

  // ── Auto-fill TRD: Unidad ────────────────────────────────────────────────────
  getOficinasDeUnidad(): string[] {
    return this.unidadesOrganicas
      .filter((u: any) => u.unidad === this.nuevaTRD.unidad)
      .map((u: any) => u.oficina);
  }

  onTRDUnidadChange() {
    const found = this.unidadesOrganicas.find((u: any) => u.unidad === this.nuevaTRD.unidad);
    this.nuevaTRD.codUnidad = found?.cod_unidad || '';
    this.nuevaTRD.oficina = '';
    this.nuevaTRD.codOficina = '';
  }

  onTRDCodUnidadChange() {
    const found = this.unidadesOrganicas.find((u: any) => u.cod_unidad === this.nuevaTRD.codUnidad);
    if (found) {
      this.nuevaTRD.unidad = found.unidad;
      this.nuevaTRD.oficina = '';
      this.nuevaTRD.codOficina = '';
    }
  }

  onTRDOficinaChange() {
    const found = this.unidadesOrganicas.find(
      (u: any) => u.unidad === this.nuevaTRD.unidad && u.oficina === this.nuevaTRD.oficina
    );
    this.nuevaTRD.codOficina = found?.cod_oficina || '';
  }

  onTRDCodOficinaChange() {
    const found = this.unidadesOrganicas.find((u: any) => u.cod_oficina === this.nuevaTRD.codOficina);
    if (found) {
      this.nuevaTRD.unidad = found.unidad;
      this.nuevaTRD.codUnidad = found.cod_unidad || '';
      this.nuevaTRD.oficina = found.oficina;
    }
  }

  // ── Auto-fill TRD: Serie ─────────────────────────────────────────────────────
  onTRDCodSerieChange() {
    const found = this.catalogoSeries.find(s => s.cod_serie === this.nuevaTRD.codSerie);
    this.nuevaTRD.nombreSerie = found ? found.nombre_serie : '';
    this.nuevaTRD.codSubserie = '';
    this.nuevaTRD.nombreSubserie = '';
    // Cargar subseries de esta serie
    if (found) {
      this.http.get<any[]>(`${this.apiUrl}/admin/catalogo-subseries?cod_serie=${found.cod_serie}`)
        .subscribe({ next: (res) => { this.catalogoSubseriesTRD = res; this.cd.detectChanges(); } });
    } else {
      this.catalogoSubseriesTRD = [];
    }
  }

  onTRDNombreSerieChange() {
    const found = this.catalogoSeries.find(s => s.nombre_serie === this.nuevaTRD.nombreSerie);
    this.nuevaTRD.codSerie = found ? found.cod_serie : '';
    this.nuevaTRD.codSubserie = '';
    this.nuevaTRD.nombreSubserie = '';
    if (found) {
      this.http.get<any[]>(`${this.apiUrl}/admin/catalogo-subseries?cod_serie=${found.cod_serie}`)
        .subscribe({ next: (res) => { this.catalogoSubseriesTRD = res; this.cd.detectChanges(); } });
    } else {
      this.catalogoSubseriesTRD = [];
    }
  }

  // ── Auto-fill TRD: Subserie ──────────────────────────────────────────────────
  onTRDCodSubserieChange() {
    const found = this.catalogoSubseriesTRD.find(s => s.cod_subserie === this.nuevaTRD.codSubserie);
    this.nuevaTRD.nombreSubserie = found ? found.nombre_subserie : '';
  }

  onTRDNombreSubserieChange() {
    const found = this.catalogoSubseriesTRD.find(s => s.nombre_subserie === this.nuevaTRD.nombreSubserie);
    this.nuevaTRD.codSubserie = found ? found.cod_subserie : '';
  }

  agregarDependencia() {
    if (!this.nuevaDependencia.codUnidad || !this.nuevaDependencia.unidadNombre) {
      Swal.fire('Campos incompletos', 'El código y nombre de la unidad administrativa son obligatorios.', 'warning');
      return;
    }

    const payload = {
      entidad: this.entidadInfo.nombre,
      cod_unidad: this.nuevaDependencia.codUnidad,
      unidad_administrativa: this.nuevaDependencia.unidadNombre,
      cod_oficina: this.nuevaDependencia.codOficina,
      oficina_productora: this.nuevaDependencia.oficinaNombre
    };

    this.http.post(`${this.apiUrl}/admin/registrar-dependencia`, payload)
      .subscribe({
        next: () => {
          Swal.fire('✅ Guardado', 'Dependencia registrada correctamente.', 'success');
          this.cargarEstructura();
          this.nuevaDependencia = { codUnidad: '', unidadNombre: '', codOficina: '', oficinaNombre: '' };
          this.mostrarModalDependencia = false;
          this.cd.detectChanges();
        },
        error: (err) => {
          Swal.fire('Error', err.error?.detail || 'No se pudo guardar la dependencia.', 'error');
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

  validarFormulario(): boolean {
    this.erroresForm = {};
    const esNOR = this.tabActivaVentanilla === 'no-radicables';

    if (!this.radicado.nombreRemitente?.trim())
      this.erroresForm['nombreRemitente'] = 'Campo requerido';
    if (!this.radicado.asunto?.trim())
      this.erroresForm['asunto'] = 'Campo requerido';
    if (!esNOR && !this.radicado.serie)
      this.erroresForm['serie'] = 'Seleccione una serie';
    if (!this.archivoBinarioPrincipal)
      this.erroresForm['archivoPrincipal'] = 'Debe adjuntar el documento principal';
    if (this.radicado.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.radicado.correo))
      this.erroresForm['correo'] = 'Correo electrónico no válido';
    return Object.keys(this.erroresForm).length === 0;
  }

  ejecutarRadicacion() {
    this.formSubmitted = true;
    if (!this.validarFormulario()) return;

    // Normalizar campos de texto a mayúsculas antes de enviar
    const camposTexto: (keyof typeof this.radicado)[] = [
      'primerApellido', 'segundoApellido', 'nombreRemitente', 'cargo',
      'telefono', 'direccion', 'asunto', 'nroGuia', 'anexoNombre',
      'descripcionAnexo', 'conCopia', 'seccionResponsable',
      'funcionarioResponsable', 'seccionOrigen', 'funcionarioOrigen'
    ];
    camposTexto.forEach(k => {
      const v = this.radicado[k];
      if (typeof v === 'string') (this.radicado as any)[k] = v.toUpperCase();
    });

    // 3. Mapeo de Metadata: De Angular (CamelCase) a Python (SnakeCase)
    const metadata = {
      tipo_radicado: ({ recibidas: 'RECIBIDA', enviadas: 'ENVIADA', internas: 'INTERNA', 'no-radicables': 'NO-RADICABLE' } as Record<string,string>)[this.tabActivaVentanilla] ?? 'NO-RADICABLE',
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
    formData.append('archivo_principal', this.archivoBinarioPrincipal!);
    
    // Agregar múltiples anexos si existen
    if (this.anexosBinarios.length > 0) {
      this.anexosBinarios.forEach((file) => {
        formData.append('anexos', file);
      });
    }

    // 5. Envío al Backend (FastAPI)
    this.http.post<any>(`${this.apiUrl}/radicar`, formData)
      .subscribe({
        next: (res) => {
          const nroGenerado = res.nro_radicado || res.numero || '—';
          const esNOR = this.tabActivaVentanilla === 'no-radicables';
          // Guardar datos del remitente ANTES de limpiar el formulario
          const nombreRemitente = this.radicado.nombreRemitente || this.radicado.primerApellido || '---';
          const tabActual = this.tabActivaVentanilla;
          this.limpiarFormularioRadicacion();
          this.obtenerEventos();
          this.cargarRadicados();

          if (esNOR) {
            // NOR: mostrar confirmación simple con opción de imprimir registro
            Swal.fire({
              icon: 'success',
              title: '✅ Registro Guardado',
              html: `
                <div style="text-align:center; font-family:'Inter',sans-serif; line-height:2;">
                  <p style="color:#64748b; font-size:0.9rem;">Comunicación no radicable registrada</p>
                  <p><span style="color:#ea580c; font-size:1.2rem; font-weight:900;">${nroGenerado}</span></p>
                  <p style="font-size:0.78rem; color:#94a3b8;">SIN RADICADO — Solo control de recepción</p>
                </div>
              `,
              showCancelButton: true,
              confirmButtonText: '🖨️ Imprimir Registro',
              cancelButtonText: '← Volver',
              confirmButtonColor: '#ea580c',
              cancelButtonColor: '#64748b',
              allowOutsideClick: false,
            }).then((result) => {
              if (result.isConfirmed) {
                this.imprimirRegistroNOR(nroGenerado, nombreRemitente);
              }
            });
          } else {
            Swal.fire({
              icon: 'success',
              title: '¡Radicado Generado!',
              html: `
                <div style="text-align:left; font-family: 'Inter', sans-serif; line-height: 2;">
                  <p><strong>N° Radicado:</strong> <span style="color:#2563eb; font-size:1.1rem; font-weight:900;">${nroGenerado}</span></p>
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
                this.imprimirStickerPDF(nroGenerado, res.vencimiento, nombreRemitente, tabActual);
              }
            });
          }
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

async imprimirStickerPDF(nroRadicado: string, vencimiento: string, nombreRemitente?: string, tab?: string) {
    const tabUsada = tab ?? this.tabActivaVentanilla;
    const labelMap: Record<string, string> = {
      'recibidas':    'ALCALDÍA DE MANIZALES (ENTRADA)',
      'enviadas':     'ALCALDÍA DE MANIZALES (SALIDA)',
      'internas':     'ALCALDÍA DE MANIZALES (INTERNA)',
      'no-radicables':'ALCALDÍA DE MANIZALES (NO RADICABLE)'
    };
    const label = labelMap[tabUsada] ?? 'ALCALDÍA DE MANIZALES';

    const qrData = `SIADE|${nroRadicado}|${new Date().toISOString()}`;
    const qrDataUrl: string = await QRCode.toDataURL(qrData, { width: 200, margin: 1 });
    const barcodeDataUrl: string = this.generarBarcodeCanvas(nroRadicado, 320, 56);

    const doc = new jsPDF({ unit: 'mm', format: [80, 110] });

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

    // Código de barras Code 128
    doc.addImage(barcodeDataUrl, 'PNG', 5, 69, 70, 12);

    // Línea separadora
    doc.setDrawColor(226, 232, 240);
    doc.line(5, 83, 75, 83);

    // Datos
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');

    const isInterna = tabUsada === 'internas';
    if (isInterna) {
      doc.text('Remite:', 5, 89);
      doc.setFont('helvetica', 'normal');
      doc.text(this.radicado.funcionarioOrigen || '---', 25, 89);
      doc.setFont('helvetica', 'bold');
      doc.text('Destino:', 5, 95);
      doc.setFont('helvetica', 'normal');
      doc.text(this.radicado.funcionarioResponsable || '---', 25, 95);
    } else {
      const personLabel = tabUsada === 'enviadas' ? 'Destinatario:' : 'Remitente:';
      doc.text(personLabel, 5, 89);
      doc.setFont('helvetica', 'normal');
      doc.text(nombreRemitente || this.radicado.nombreRemitente || '---', 30, 89);
      doc.setFont('helvetica', 'bold');
      doc.text('Vencimiento:', 5, 95);
      doc.setFont('helvetica', 'normal');
      doc.text(vencimiento, 30, 95);
    }

    doc.setFont('helvetica', 'bold');
    doc.text('Fecha:', 5, 101);
    doc.setFont('helvetica', 'normal');
    doc.text(this.fechaActualRadicado, 25, 101);

    // Abrir diálogo de impresión (incluye opción "Guardar como PDF" en el navegador)
    doc.autoPrint();
    const blob = doc.output('blob');
    const url = URL.createObjectURL(blob);
    const ventana = window.open(url, '_blank');
    if (ventana) {
      ventana.addEventListener('load', () => {
        ventana.print();
        URL.revokeObjectURL(url);
      });
    } else {
      // Fallback si el navegador bloquea popups: descarga directa
      doc.save(`sticker_${nroRadicado}.pdf`);
      URL.revokeObjectURL(url);
    }
  }

// ── Registro NOR (sin QR, sin sticker) ──────────────────────────────────────
imprimirRegistroNOR(nroRegistro: string, nombreRemitente?: string) {
  const doc = new jsPDF({ unit: 'mm', format: [80, 100] });

  // Fondo naranja header
  doc.setFillColor(234, 88, 12);
  doc.rect(0, 0, 80, 20, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  doc.text('S  I  A  D  E', 40, 8, { align: 'center' });
  doc.setFontSize(5.5);
  doc.setFont('helvetica', 'normal');
  doc.text('REGISTRO DE COMUNICACIÓN NO RADICABLE', 40, 14, { align: 'center' });

  // Ícono de documento (simulado con texto)
  doc.setFontSize(22);
  doc.setTextColor(249, 115, 22);
  doc.text('📄', 40, 35, { align: 'center' });

  // Entidad
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100, 116, 139);
  doc.text('ALCALDÍA DE MANIZALES', 40, 44, { align: 'center' });

  // NOR número
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(234, 88, 12);
  doc.text(nroRegistro, 40, 52, { align: 'center' });

  // Datos
  doc.setFontSize(7);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(71, 85, 105);
  doc.text(`Remitente: ${nombreRemitente || this.radicado.nombreRemitente || '---'}`, 40, 62, { align: 'center' });
  doc.text(this.fechaActualRadicado, 40, 68, { align: 'center' });

  // Etiqueta SIN RADICADO
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(234, 88, 12);
  doc.text('SIN RADICADO', 40, 76, { align: 'center' });

  // Línea separadora
  doc.setDrawColor(226, 232, 240);
  doc.line(5, 80, 75, 80);

  doc.setFontSize(5.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(148, 163, 184);
  doc.text('Solo control de recepción — No genera trámite', 40, 86, { align: 'center' });

  // Abrir diálogo de impresión
  doc.autoPrint();
  const blob = doc.output('blob');
  const url = URL.createObjectURL(blob);
  const ventana = window.open(url, '_blank');
  if (ventana) {
    ventana.addEventListener('load', () => { ventana.print(); URL.revokeObjectURL(url); });
  } else {
    doc.save(`registro_nor_${nroRegistro}.pdf`);
    URL.revokeObjectURL(url);
  }
}

// ── Días hábiles Colombia ────────────────────────────────────────────────────
private readonly FESTIVOS_CO = new Set([
  // 2025
  '2025-01-01','2025-01-06','2025-03-24','2025-04-17','2025-04-18',
  '2025-05-01','2025-06-02','2025-06-23','2025-06-30',
  '2025-07-20','2025-08-07','2025-08-18','2025-10-13',
  '2025-11-03','2025-11-17','2025-12-08','2025-12-25',
  // 2026
  '2026-01-01','2026-01-12','2026-03-23','2026-04-02','2026-04-03',
  '2026-05-01','2026-05-18','2026-06-08','2026-06-15','2026-06-29',
  '2026-07-20','2026-08-07','2026-08-17','2026-10-12',
  '2026-11-02','2026-11-16','2026-12-08','2026-12-25',
]);

calcularFechaVencimiento(diasHabiles: number): string {
  const fecha = new Date();
  let contados = 0;
  while (contados < diasHabiles) {
    fecha.setDate(fecha.getDate() + 1);
    const diaSemana = fecha.getDay(); // 0=Dom, 6=Sab
    const iso = fecha.toISOString().slice(0, 10);
    if (diaSemana !== 0 && diaSemana !== 6 && !this.FESTIVOS_CO.has(iso)) {
      contados++;
    }
  }
  return fecha.toISOString().slice(0, 10);
}

onDiasRespuestaChange() {
  const dias = Number(this.radicado.diasRespuesta);
  if (dias > 0) {
    this.radicado.fechaVencimiento = this.calcularFechaVencimiento(dias);
  }
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

  // Resetear validación
  this.formSubmitted = false;
  this.erroresForm = {};

  this.cd.detectChanges();
}

  // --- GESTIÓN DE TRD (VÍNCULO CON FASTAPI Y JSONB) ---

  cargarTRD() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-trd`)
      .subscribe({
        next: (res) => {
          this.listaTRD = res;
          this.cd.detectChanges();
        },
        error: () => console.warn("Error al cargar TRD.")
      });
  }

  cargarCatalogoSeries() {
    this.http.get<any[]>(`${this.apiUrl}/admin/catalogo-series`)
      .subscribe({
        next: (res) => {
          this.catalogoSeries = res;
          this.cd.detectChanges();
        },
        error: () => console.warn("Error al cargar catálogo de series.")
      });
  }

  onSerieChange() {
    const serieSeleccionada = this.catalogoSeries.find(
      s => s.nombre_serie === this.radicado.serie
    );
    this.radicado.subserie = '';
    this.catalogoSubseries = [];
    if (serieSeleccionada) {
      this.http.get<any[]>(`${this.apiUrl}/admin/catalogo-subseries?cod_serie=${serieSeleccionada.cod_serie}`)
        .subscribe({
          next: (res) => {
            this.catalogoSubseries = res;
            this.cd.detectChanges();
          },
          error: () => console.warn("Error al cargar subseries.")
        });
    }
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

    this.http.post(`${this.apiUrl}/admin/registrar-trd`, payloadTRD)
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
    this.http.post(`${this.apiUrl}/admin/crear-equipo`, payload)
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

    this.http.get<any[]>(`${this.apiUrl}/admin/listar-equipos`)
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

    this.http.post(`${this.apiUrl}/admin/asignar-equipos-usuario`, payload)
      .subscribe({
        next: () => {
          alert(`✅ Grupos vinculados a ${this.usuarioSeleccionado.nombre_completo}`);
          this.cerrarModales();
        },
        error: (err) => alert("❌ Error en la actualización.")
      });
  }

  cargarListaGrupos() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-equipos`)
      .subscribe(res => this.listaEquipos = res);
  }

  cargarKpis() {
    this.http.get<any>(`${this.apiUrl}/admin/kpi-dashboard`).subscribe({
      next: (res) => { this.kpi = res; this.cd.detectChanges(); },
      error: () => {}
    });
  }

  ngAfterViewInit() {
    // Las gráficas se crean cuando lleguen los datos
  }

  cargarGraficas() {
    this.http.get<any>(`${this.apiUrl}/admin/stats-graficas`).subscribe({
      next: (res) => {
        this.graficasListas = true;
        this.cd.detectChanges();
        // Dar tiempo al navegador para que pinte los canvas antes de inicializar Chart.js
        setTimeout(() => { this._inicializarGraficas(res); }, 150);
      },
      error: (err) => { console.error('stats-graficas error:', err); }
    });
  }

  private _inicializarGraficas(data: any) {
    // --- Gráfica de barras: últimos 7 días por tipo ---
    if (this.chartBarrasRef?.nativeElement) {
      if (this.chartBarras) { this.chartBarras.destroy(); }
      const colores: Record<string, string> = {
        'RECIBIDA':     '#3b82f6',
        'ENVIADA':      '#10b981',
        'INTERNA':      '#8b5cf6',
        'NO-RADICABLE': '#f59e0b'
      };
      const datasets = Object.entries(data.barras.series).map(([tipo, valores]) => ({
        label: tipo,
        data: valores as number[],
        backgroundColor: colores[tipo] || '#64748b',
        borderRadius: 4,
        borderSkipped: false as const
      }));
      this.chartBarras = new Chart(this.chartBarrasRef.nativeElement, {
        type: 'bar',
        data: { labels: data.barras.labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
            title: { display: false }
          },
          scales: {
            x: { stacked: false, grid: { display: false }, ticks: { font: { size: 11 } } },
            y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 11 } }, grid: { color: '#f1f5f9' } }
          }
        }
      });
    }

    // --- Gráfica de dona: distribución por estado ---
    if (this.chartDonaRef?.nativeElement) {
      if (this.chartDona) { this.chartDona.destroy(); }
      const paleta = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'];
      this.chartDona = new Chart(this.chartDonaRef.nativeElement, {
        type: 'doughnut',
        data: {
          labels: data.dona.labels,
          datasets: [{
            data: data.dona.values,
            backgroundColor: paleta.slice(0, data.dona.labels.length),
            borderWidth: 2,
            borderColor: '#fff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
          },
          cutout: '65%'
        }
      });
    }
  }

  cargarRadicados(page: number = this.paginacionRadicados.page) {
    const p: any = { page, per_page: this.paginacionRadicados.per_page };
    if (this.busquedaRadicados.trim())        p['q']            = this.busquedaRadicados.trim();
    if (this.filtrosGestion.tipo)             p['tipo_doc']     = this.filtrosGestion.tipo;
    if (this.filtrosGestion.estado)           p['estado']       = this.filtrosGestion.estado;
    if (this.filtrosGestion.serie)            p['serie_filtro'] = this.filtrosGestion.serie;
    if (this.filtrosGestion.vencido)          p['vencido']      = this.filtrosGestion.vencido;

    this.http.get<any>(`${this.apiUrl}/radicados`, { params: p })
      .subscribe({
        next: (res) => {
          this.listaRadicados = res.items ?? res;
          this.paginacionRadicados = {
            page:        res.page       ?? 1,
            per_page:    res.per_page   ?? 50,
            total:       res.total      ?? res.length ?? 0,
            total_pages: res.total_pages ?? 1
          };
          setTimeout(() => this.cd.detectChanges(), 0);
        },
        error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudieron cargar los radicados.', 'error')
      });
  }

  cambiarPaginaRadicados(page: number) {
    if (page < 1 || page > this.paginacionRadicados.total_pages) return;
    this.paginacionRadicados.page = page;
    this.cargarRadicados(page);
  }

  aplicarFiltrosRadicados() {
    this.paginacionRadicados.page = 1;
    this.cargarRadicados(1);
  }

  cargarUsuariosActivos() {
    this.http.get<any[]>(`${this.apiUrl}/usuarios-activos`)
      .subscribe({ next: (res) => { this.usuariosActivos = res; this.cd.detectChanges(); } });
  }

  getCorreoFuncionario(nombreCompleto: string): string {
    const u = this.usuariosActivos.find(u => u.nombre_completo === nombreCompleto);
    return u?.correo || '';
  }

  cargarNotificaciones() {
    this.http.get<any[]>(`${this.apiUrl}/mis-notificaciones`)
      .subscribe({ next: (res) => { this.notificaciones = res; this.cd.detectChanges(); } });
  }

  get notificacionesSinLeer(): number {
    return this.notificaciones.filter(n => !n.leida).length;
  }

  marcarLeida(id: number) {
    this.http.post(`${this.apiUrl}/mis-notificaciones/${id}/leer`, {})
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
      
    ).subscribe({
      next: (res) => { this.historialActual = res; this.cargandoHistorial = false; this.cd.detectChanges(); },
      error: () => { this.cargandoHistorial = false; this.cd.detectChanges(); Swal.fire('Error', 'No se pudo cargar el historial.', 'error'); }
    });
  }

  async abrirFlujo(radicado: any) {
    this.radicadoFlujoActual = radicado;
    this.mostrarModalFlujo = true;
    this.cargandoFlujo = true;
    this.cd.detectChanges();

    // Obtener info del flujo desde el backend
    this.http.get<any>(
      `${this.apiUrl}/radicados/${encodeURIComponent(radicado.nro_radicado)}/flujo`,
      
    ).subscribe({
      next: async (flujoData) => {
        this.radicadoFlujoActual = { ...radicado, ...flujoData };
        this.flujoTieneInstancia = flujoData.tiene_instancia_real;
        this.pasoActualFlujo = flujoData.paso_actual;
        this.cd.detectChanges();
        await this.renderizarBpmnModal(flujoData);
      },
      error: () => {
        this.cargandoFlujo = false;
        this.cd.detectChanges();
        Swal.fire('Error', 'No se pudo cargar el flujo de trabajo.', 'error');
      }
    });
  }

  iniciarFlujoWorkflow() {
    if (!this.radicadoFlujoActual) return;
    const formData = new FormData();
    formData.append('nro_radicado', this.radicadoFlujoActual.nro_radicado);
    this.http.post<any>(`${this.apiUrl}/workflows/start`, formData)
      .subscribe({
        next: (res) => {
          this.flujoTieneInstancia = true;
          this.pasoActualFlujo = res.paso_actual;
          this.abrirFlujo(this.radicadoFlujoActual);
        },
        error: () => Swal.fire('Error', 'No se pudo iniciar el flujo.', 'error')
      });
  }

  avanzarPasoFlujo() {
    if (!this.radicadoFlujoActual) return;
    const nro = encodeURIComponent(this.radicadoFlujoActual.nro_radicado);
    this.http.post<any>(`${this.apiUrl}/workflows/${nro}/complete-task`, {})
      .subscribe({
        next: (res) => {
          this.pasoActualFlujo = res.paso_actual;
          this.radicadoFlujoActual.estado = res.estado_radicado;
          this.abrirFlujo(this.radicadoFlujoActual);
        },
        error: () => Swal.fire('Error', 'No se pudo avanzar el paso.', 'error')
      });
  }

  async renderizarBpmnModal(flujoData: any) {
    await new Promise(r => setTimeout(r, 100)); // esperar que el DOM esté listo

    if (this.bpmnModalViewer) {
      this.bpmnModalViewer.destroy();
    }

    const container = this.bpmnModalContainer?.nativeElement;
    if (!container) { this.cargandoFlujo = false; this.cd.detectChanges(); return; }

    this.bpmnModalViewer = new BpmnViewer({ container });

    try {
      const response = await fetch(`/bpmn/${flujoData.archivo_bpmn}`);
      const xml = await response.text();
      await this.bpmnModalViewer.importXML(xml);

      const canvas = this.bpmnModalViewer.get('canvas');
      canvas.zoom('fit-viewport', 'auto');

      // Colorear pasos completados (verde)
      for (const paso of flujoData.pasos_completados || []) {
        try { canvas.addMarker(paso, 'flujo-completado'); } catch {}
      }
      // Colorear paso actual (azul)
      try { canvas.addMarker(flujoData.paso_actual, 'flujo-actual'); } catch {}

    } catch (e) {
      console.error('Error renderizando BPMN:', e);
    } finally {
      this.cargandoFlujo = false;
      this.cd.detectChanges();
    }
  }

  ajustarVistaFlujo() {
    if (this.bpmnModalViewer) {
      this.bpmnModalViewer.get('canvas').zoom('fit-viewport', 'auto');
    }
  }

  cerrarModalFlujo() {
    this.mostrarModalFlujo = false;
    if (this.bpmnModalViewer) {
      this.bpmnModalViewer.destroy();
      this.bpmnModalViewer = null;
    }
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
    this.http.get<any[]>(`${this.apiUrl}/archivo-central`, { params })
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
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: blob => {
        if (this._pdfBlobUrl) URL.revokeObjectURL(this._pdfBlobUrl);
        this._pdfBlobUrl = URL.createObjectURL(blob);
        this.pdfUrlSegura = this.sanitizer.bypassSecurityTrustResourceUrl(this._pdfBlobUrl);
        this.pdfNroRadicado = nroRadicado;
        this.mostrarModalPdf = true;
      },
      error: () => Swal.fire('Sin documento', 'No se encontró el archivo adjunto para este radicado.', 'info')
    });
  }

  descargarDocumentoRadicado(nroRadicado: string) {
    const url = `${this.apiUrl}/radicados/${encodeURIComponent(nroRadicado)}/documento`;
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${nroRadicado}.pdf`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      },
      error: () => Swal.fire('Sin documento', 'No se encontró el archivo adjunto.', 'info')
    });
  }

  cerrarModalPdf() {
    this.mostrarModalPdf = false;
    if (this._pdfBlobUrl) {
      URL.revokeObjectURL(this._pdfBlobUrl);
      this._pdfBlobUrl = '';
    }
    this.pdfUrlSegura = null;
  }

  // Filtrado ahora es server-side — este getter solo retorna la página actual
  get radicadosFiltrados(): any[] {
    return this.listaRadicados;
  }

  limpiarFiltrosGestion() {
    this.busquedaRadicados = '';
    this.filtrosGestion = { tipo: '', estado: '', serie: '', vencido: '' };
    this.aplicarFiltrosRadicados();
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

    this.http.post(`${this.apiUrl}${endpoint}`, formData)
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
    this.mostrarModalConfig = false;
    this.formCambioPassword = { password_actual: '', password_nuevo: '', password_confirmar: '' };
    this.errorCambioPassword = '';
    this.mostrarModalCambioPassword = true;
    this.cd.detectChanges();
  }

  confirmarCambioPassword() {
    this.errorCambioPassword = '';
    const { password_actual, password_nuevo, password_confirmar } = this.formCambioPassword;

    // Validaciones frontend
    if (!this.esCambioForzado && !password_actual) {
      this.errorCambioPassword = 'Ingresa tu contraseña actual.';
      return;
    }
    if (!password_nuevo || !password_confirmar) {
      this.errorCambioPassword = 'Completa todos los campos.';
      return;
    }
    if (password_nuevo.length < 6) {
      this.errorCambioPassword = 'La nueva contraseña debe tener al menos 6 caracteres.';
      return;
    }
    if (/^\d+$/.test(password_nuevo)) {
      this.errorCambioPassword = 'La contraseña no puede ser solo números.';
      return;
    }
    if (/^[a-zA-Z]+$/.test(password_nuevo)) {
      this.errorCambioPassword = 'La contraseña debe incluir al menos un número.';
      return;
    }
    if (password_nuevo !== password_confirmar) {
      this.errorCambioPassword = 'Las contraseñas no coinciden.';
      return;
    }

    const endpoint = this.esCambioForzado
      ? `${this.apiUrl}/auth/cambiar-password-inicial`
      : `${this.apiUrl}/auth/cambiar-password`;

    const payload = this.esCambioForzado
      ? { password_actual: '', password_nuevo, password_confirmar }
      : { password_actual, password_nuevo, password_confirmar };

    this.http.post(endpoint, payload)
      .subscribe({
        next: () => {
          localStorage.removeItem('debe_cambiar_password');
          this.esCambioForzado = false;
          this.cerrarModales();
          Swal.fire({
            icon: 'success',
            title: '¡Bienvenido a SIADE!',
            text: 'Tu contraseña ha sido configurada. Ya puedes usar el sistema.',
            confirmButtonColor: '#2563eb'
          });
        },
        error: (err) => {
          this.errorCambioPassword = err.error?.detail || 'Error al cambiar la contraseña.';
          this.cd.detectChanges();
        }
      });
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
    this.mostrarModalCambioPassword = false;
    this.usuarioSeleccionado = null;
    this.nombreNuevoGrupo = '';
    this.pasoCreacionGrupo = 1;
    this.formCambioPassword = { password_actual: '', password_nuevo: '', password_confirmar: '' };
    this.errorCambioPassword = '';
  }

  // --- GESTIÓN DE DATOS ---

  cargarUsuarios() {
    this.http.get<any[]>(`${this.apiUrl}/admin/listar-usuarios`)
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

      // console.log(`%c--- SOLICITANDO CAMBIO DE ESTADO (ID: ${user.id}) ---`, "color: #f43f5e; font-weight: bold;");

      this.http.post(`${this.apiUrl}/admin/cambiar-estado-usuario`, payload)
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

  generarTokenReset(user: any) {
    if (!confirm(`¿Generar token de recuperación de contraseña para ${user.nombre_completo}?`)) return;

    const formData = new FormData();
    formData.append('usuario', user.usuario);

    this.http.post<any>(`${this.apiUrl}/auth/solicitar-reset`, formData)
      .subscribe({
        next: (res) => {
          Swal.fire({
            title: '🔑 Token generado',
            html: `
              <p style="margin-bottom:12px">Entrega este token a <strong>${user.nombre_completo}</strong>:</p>
              <div style="background:#f1f5f9;padding:12px;border-radius:8px;font-family:monospace;font-size:13px;word-break:break-all;margin-bottom:8px">
                ${res.token}
              </div>
              <p style="font-size:12px;color:#94a3b8">⏱️ Expira en 2 horas</p>
            `,
            confirmButtonText: '📋 Copiar token',
            showCancelButton: true,
            cancelButtonText: 'Cerrar',
            confirmButtonColor: '#2563eb'
          }).then(result => {
            if (result.isConfirmed) {
              navigator.clipboard.writeText(res.token);
              Swal.fire({ title: '✅ Copiado', text: 'Token copiado al portapapeles', icon: 'success', timer: 1500, showConfirmButton: false });
            }
          });
        },
        error: (err) => alert('❌ Error: ' + (err.error?.detail || 'No se pudo generar el token'))
      });
  }

  iniciarMonitoreo() {
    this.obtenerEventos();
    this.auditSubscription = interval(10000).subscribe(() => {
      this.obtenerEventos();
    });
  }

  obtenerEventos() {
    this.http.get<any[]>(`${this.apiUrl}/admin/eventos-recientes`)
      .subscribe({
        next: (res) => this.eventosRecientes = res,
        error: (err) => console.error('Error en feed de auditoría', err)
      });
  }

  // ----- SERIES Y SUBSERIES CREADAS POR TRD
  getSeriesUnicas() {
    return this.catalogoSeries.map(s => ({
      nombre: s.nombre_serie,
      etiqueta: `${s.cod_serie} - ${s.nombre_serie}`
    }));
  }

  getSubseriesUnicas() {
    return this.catalogoSubseries.map(sub => {
      // Mostrar solo el número propio (ej: "02-01" → "01")
      const partes = sub.cod_subserie.split('-');
      const codCorto = partes.length > 1 ? partes.slice(1).join('-') : sub.cod_subserie;
      return {
        nombre: sub.nombre_subserie,
        etiqueta: `${codCorto} - ${sub.nombre_subserie}`
      };
    });
  }

  getTiposDocumentalesUnicos() {
    if (!this.radicado.serie || !this.listaTRD) return [];
    const tipos = this.listaTRD
      .filter(item => (item.serie || '').toString() === this.radicado.serie.toString())
      .map(item => (item.tipo_documental || '').toString().trim());
    return [...new Set(tipos)].filter(t => t !== '');
  }

  // Lista demo — reemplazar con datos reales de TRD cuando estén disponibles
  tiposDocumentalesDemo: string[] = [
    'Queja, informe',
    'Auto inhibitorio',
    'Auto de apertura',
    'Citación de notificación',
    'Edicto',
    'Práctica de pruebas ordenadas',
    'Recurso de apelación',
    'Auto de investigación',
    'Auto de prórroga',
    'Auto de pliego de cargos',
    'Auto de archivo',
    'Defensor de oficio',
    'Auto de pruebas',
    'Recurso en primera instancia',
    'Alegato de conclusión',
    'Fallo de primera instancia',
    'Recurso proceso disciplinario',
    'Fallo de segunda instancia',
    'Antecedentes disciplinarios',
    'Acto administrativo'
  ];

  getTiposParaSelect(): string[] {
    const fromTRD = this.getTiposDocumentalesUnicos();
    return fromTRD.length > 0 ? fromTRD : this.tiposDocumentalesDemo;
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

    this.http.post<any>(`${this.apiUrl}/radicar`, formData)
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

  cargarAuditLogs(page: number = 1) {
    this.auditPaginacion.page = page;
    const f = this.filtrosAudit;
    let params = `page=${page}&per_page=${this.auditPaginacion.per_page}`;
    if (f.usuario)     params += `&usuario=${encodeURIComponent(f.usuario)}`;
    if (f.modulo)      params += `&modulo=${f.modulo}`;
    if (f.fecha_desde) params += `&fecha_desde=${f.fecha_desde}`;
    if (f.fecha_hasta) params += `&fecha_hasta=${f.fecha_hasta}`;

    this.http.get<any>(`${this.apiUrl}/admin/audit-logs?${params}`)
      .subscribe({
        next: (res) => {
          this.listaAuditLogs = res.items;
          this.auditPaginacion = { page: res.page, per_page: res.per_page, total: res.total, total_pages: res.total_pages };
          this.cd.detectChanges();
        },
        error: () => Swal.fire('Error', 'No se pudieron cargar los logs de auditoría.', 'error')
      });
  }

  cambiarPaginaAudit(page: number) {
    if (page < 1 || page > this.auditPaginacion.total_pages) return;
    this.cargarAuditLogs(page);
  }

  exportarAuditCSV() {
    const f = this.filtrosAudit;
    let params = '';
    if (f.usuario)     params += `&usuario=${encodeURIComponent(f.usuario)}`;
    if (f.modulo)      params += `&modulo=${f.modulo}`;
    if (f.fecha_desde) params += `&fecha_desde=${f.fecha_desde}`;
    if (f.fecha_hasta) params += `&fecha_hasta=${f.fecha_hasta}`;

    const url = `${this.apiUrl}/admin/audit-logs/export?${params.substring(1)}`;

    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        const fecha = new Date().toISOString().slice(0, 10);
        a.download = `auditoria_siade_${fecha}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      },
      error: () => Swal.fire('Error', 'No se pudo exportar el CSV.', 'error')
    });
  }

  crearUsuario() {
    if (!this.nuevoUser.nombre.trim() || !this.nuevoUser.usuario.trim()) {
      Swal.fire('Campos incompletos', 'El nombre y el ID de usuario son obligatorios.', 'warning');
      return;
    }

    const payload = {
      usuario: this.nuevoUser.usuario.trim().toLowerCase(),
      nombre_completo: this.nuevoUser.nombre.trim(),
      rol_id: this.nuevoUser.rol_id
    };

    this.http.post(`${this.apiUrl}/admin/crear-usuario`, payload)
      .subscribe({
        next: (res: any) => {
          this.cerrarModales();
          this.nuevoUser = { nombre: '', usuario: '', rol_id: 3 };
          this.obtenerEventos();

          const roles: Record<number, string> = { 1: 'Administrador', 2: 'Usuario Productor', 3: 'Usuario Consultor' };
          Swal.fire({
            icon: 'success',
            title: '✅ Funcionario Registrado',
            html: `
              <p style="margin-bottom:1rem;color:#64748b;">Comparte estos datos con el funcionario de forma segura:</p>
              <table style="width:100%;border-collapse:collapse;font-size:0.9rem;text-align:left;">
                <tr style="border-bottom:1px solid #e2e8f0;">
                  <td style="padding:0.5rem;font-weight:700;color:#475569;">Usuario</td>
                  <td style="padding:0.5rem;font-family:monospace;color:#1e293b;">${res.usuario ?? payload.usuario}</td>
                </tr>
                <tr style="border-bottom:1px solid #e2e8f0;">
                  <td style="padding:0.5rem;font-weight:700;color:#475569;">Rol</td>
                  <td style="padding:0.5rem;color:#1e293b;">${roles[payload.rol_id] ?? payload.rol_id}</td>
                </tr>
                <tr style="border-bottom:1px solid #e2e8f0;">
                  <td style="padding:0.5rem;font-weight:700;color:#475569;">Contraseña temporal</td>
                  <td style="padding:0.5rem;font-family:monospace;font-weight:900;color:#dc2626;">${res.password_temporal}</td>
                </tr>
                <tr>
                  <td style="padding:0.5rem;font-weight:700;color:#475569;">Código 2FA</td>
                  <td style="padding:0.5rem;font-family:monospace;color:#2563eb;">${res.secret_2fa}</td>
                </tr>
              </table>
              <p style="margin-top:1rem;font-size:0.78rem;color:#94a3b8;">El funcionario deberá cambiar su contraseña en el primer inicio de sesión.</p>
            `,
            confirmButtonText: 'Entendido',
            confirmButtonColor: '#2563eb',
            width: 520
          });
        },
        error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudo crear el usuario.', 'error')
      });
  }

    // Función para manejar la selección de archivos
  private contarPaginasPDF(file: File): Promise<number> {
    return new Promise((resolve) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) { resolve(1); return; }
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const buf = e.target?.result as ArrayBuffer;
          const text = new TextDecoder('latin1').decode(buf);
          // Buscar /Count N en el diccionario de páginas del PDF
          const matches = [...text.matchAll(/\/Count\s+(\d+)/g)];
          if (matches.length > 0) {
            // El mayor valor de /Count es el total de páginas
            const max = Math.max(...matches.map(m => parseInt(m[1], 10)));
            resolve(max);
          } else {
            // Fallback: contar ocurrencias de /Type /Page (sin 's')
            const pages = (text.match(/\/Type\s*\/Page[^s]/g) || []).length;
            resolve(pages || 1);
          }
        } catch { resolve(1); }
      };
      reader.readAsArrayBuffer(file);
    });
  }

  onFileSelected(event: any, tipo: string) {
    const files: File[] = Array.from(event.target.files);
    if (!files.length) return;

    if (tipo === 'principal') {
      this.nombreArchivoPrincipal = files[0].name;
      this.archivoBinarioPrincipal = files[0];
      // Contar páginas del principal y sumar con los anexos actuales
      this.contarPaginasPDF(files[0]).then(paginas => {
        (this as any)._paginasPrincipal = paginas;
        const paginasAnexos = (this as any)._paginasAnexos || 0;
        this.radicado.folios = Math.min(paginas + paginasAnexos, 15);
        this.cd.detectChanges();
      });
    } else {
      this.nombreArchivoAnexo = `${files.length} archivo(s) seleccionado(s)`;
      this.anexosBinarios = files;
      // Contar páginas de todos los anexos en paralelo
      Promise.all(files.map(f => this.contarPaginasPDF(f))).then(conteos => {
        const totalAnexos = conteos.reduce((a, b) => a + b, 0);
        (this as any)._paginasAnexos = totalAnexos;
        const paginasPrincipal = this.archivoBinarioPrincipal
          ? (this as any)._paginasPrincipal || 0 : 0;
        this.radicado.folios = Math.min(totalAnexos + paginasPrincipal, 15);
        this.cd.detectChanges();
      });
    }
    this.cd.detectChanges();
  }

  getRoleName(rolId: number): string {
    const roles: { [key: number]: string } = {
      0: 'Super Administrador',
      1: 'Administrador',
      2: 'Usuario Productor',
      3: 'Usuario Consultor'
    };
    return roles[rolId] || 'Funcionario SIADE';
  }

  cerrarSesion() {
    // T7.2.2 — Invalidar token en el servidor (blacklist Redis) antes de limpiar localmente
    const token = localStorage.getItem('token');
    if (token) {
      this.http.post(`${this.apiUrl}/auth/logout`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      }).subscribe({ error: () => {} }); // fire-and-forget: siempre limpiamos local
    }
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('debe_cambiar_password');
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

  // =====================================================================
  // T5.2.2 — Generador Code 128 con canvas nativo
  // =====================================================================

  /**
   * Genera un código de barras Code 128B en un canvas HTML y retorna
   * su dataURL (PNG) listo para preview o para insertar en jsPDF.
   */
  generarBarcodeCanvas(texto: string, ancho: number = 280, alto: number = 60): string {
    // Tabla de valores Code 128B (caracteres ASCII 32–127)
    const CODE128B_TABLE: number[] = [
      212222,222122,222221,121223,121322,131222,122213,122312,132212,221213,
      221312,231212,112232,122132,122231,113222,123122,123221,223211,221132,
      221231,213212,223112,312131,311222,321122,321221,312212,322112,322211,
      212123,212321,232121,111323,131123,131321,112313,132113,132311,211313,
      231113,231311,112133,112331,132131,113123,113321,133121,313121,211331,
      231131,213113,213311,213131,311123,311321,331121,312113,312311,332111,
      314111,221411,431111,111224,111422,121124,121421,141122,141221,112214,
      112412,122114,122411,142112,142211,241211,221114,413111,241112,134111,
      111242,121142,121241,114212,124112,124211,411212,421112,421211,212141,
      214121,412121,111143,111341,131141,114113,114311,411113,411311,113141,
      114131,311141,411131,211412,211214,211232,2331112
    ];

    const START_B = 104;
    const STOP    = 106;
    const FNC1    = 102;

    // Calcular checksum
    let checksum = START_B;
    const codes: number[] = [START_B];
    for (let i = 0; i < texto.length; i++) {
      const code = texto.charCodeAt(i) - 32;
      codes.push(code);
      checksum += code * (i + 1);
    }
    codes.push(checksum % 103);
    codes.push(STOP);

    // Convertir a barras (cada dígito = número de módulos)
    const barras: { ancho: number; esNegro: boolean }[] = [];
    codes.forEach((code, idx) => {
      const pattern = CODE128B_TABLE[code].toString().padStart(6, '0');
      pattern.split('').forEach((w, i) => {
        barras.push({ ancho: parseInt(w), esNegro: i % 2 === 0 });
      });
    });

    // Dibujar en canvas offscreen
    const canvas = document.createElement('canvas');
    const totalModulos = barras.reduce((s, b) => s + b.ancho, 0);
    const escala = ancho / totalModulos;
    canvas.width  = ancho;
    canvas.height = alto;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, ancho, alto);

    let x = 0;
    barras.forEach(b => {
      const w = b.ancho * escala;
      if (b.esNegro) {
        ctx.fillStyle = '#000000';
        ctx.fillRect(Math.round(x), 0, Math.max(1, Math.round(w)), alto - 12);
      }
      x += w;
    });

    // Texto debajo
    ctx.fillStyle = '#000000';
    ctx.font = `bold ${Math.max(9, alto * 0.18)}px monospace`;
    ctx.textAlign = 'center';
    ctx.fillText(texto, ancho / 2, alto - 2);

    return canvas.toDataURL('image/png');
  }

  barcodePreviewUrl: string = '';

  actualizarBarcodePreview() {
    const prefijo = this.obtenerPrefijo();
    const anio = new Date().getFullYear();
    const nro = `${prefijo}-${anio}-${this.nroRadicadoSimulado}`;
    this.barcodePreviewUrl = this.generarBarcodeCanvas(nro, 260, 52);
    this.cd.detectChanges();
  }

  async actualizarQRPreview() {
    const prefijo = this.obtenerPrefijo();
    const anio = new Date().getFullYear();
    const nro = `${prefijo}-${anio}-${this.nroRadicadoSimulado}`;
    const remitente = this.radicado.nombreRemitente || 'Sin nombre';
    const asunto = this.radicado.asunto || 'Sin asunto';
    const fecha = this.fechaActualRadicado;
    const qrData = `SIADE|${nro}|${remitente}|${asunto}|${fecha}`;
    try {
      this.qrPreviewUrl = await QRCode.toDataURL(qrData, {
        width: 180,
        margin: 1,
        color: { dark: '#0f172a', light: '#ffffff' }
      });
      this.actualizarBarcodePreview();
      this.cd.detectChanges();
    } catch (e) {
      console.error('Error generando QR preview:', e);
    }
  }

  // =====================================================================
  // T4.5.1 / T4.5.2 — Facturas Electrónicas DIAN UBL 2.1
  // =====================================================================

  cargarFacturasDian() {
    const params = this.busquedaFacturasDian ? `?q=${encodeURIComponent(this.busquedaFacturasDian)}` : '';
    this.http.get<any>(`${environment.apiUrl}/facturas/dian${params}`).subscribe({
      next: (res) => {
        this.facturasDianLista = res.facturas || [];
        this.cd.detectChanges();
      },
      error: () => { this.facturasDianLista = []; }
    });
  }

  onXmlDianSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    const archivo = input.files[0];
    this.archivoDianSeleccionado = archivo;

    // Parsear el XML (preview)
    const formData = new FormData();
    formData.append('archivo', archivo);

    Swal.fire({ title: 'Analizando XML...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

    this.http.post<any>(`${environment.apiUrl}/facturas/parsear-xml`, formData).subscribe({
      next: (res) => {
        Swal.close();
        this.previewDianData = res;
        this.mostrarModalPreviewDian = true;
        this.cd.detectChanges();
      },
      error: (err) => {
        Swal.close();
        Swal.fire('Error al procesar XML', err.error?.detail || 'Verifica que sea un XML DIAN válido.', 'error');
      }
    });

    // Reset input para permitir volver a seleccionar el mismo archivo
    input.value = '';
  }

  confirmarRadicarDian() {
    if (!this.archivoDianSeleccionado) return;
    this.cargandoRadicacionDian = true;

    const formData = new FormData();
    formData.append('archivo', this.archivoDianSeleccionado);

    this.http.post<any>(`${environment.apiUrl}/facturas/radicar-dian`, formData).subscribe({
      next: (res) => {
        this.cargandoRadicacionDian = false;
        this.mostrarModalPreviewDian = false;
        this.archivoDianSeleccionado = null;
        this.previewDianData = null;
        this.cargarFacturasDian();
        Swal.fire({
          icon: 'success',
          title: '¡Factura radicada!',
          html: `
            <div style="text-align: left; font-size: 0.9rem;">
              <p><strong>Radicado:</strong> <span style="color: #2563eb; font-size: 1.1rem;">${res.nro_radicado}</span></p>
              <p><strong>Factura:</strong> ${res.nro_factura}</p>
              <p><strong>Proveedor:</strong> ${res.proveedor}</p>
              <p><strong>Valor:</strong> $${parseFloat(res.valor_a_pagar || '0').toLocaleString('es-CO')} COP</p>
              <p><strong>Vence:</strong> ${res.fecha_vencimiento}</p>
            </div>
          `,
          confirmButtonText: 'Ver en Gestión Documental'
        }).then((result) => {
          if (result.isConfirmed) {
            this.seccionActiva = 'gestion-documental';
            this.cargarRadicados();
          }
        });
        this.cd.detectChanges();
      },
      error: (err) => {
        this.cargandoRadicacionDian = false;
        Swal.fire('Error al radicar', err.error?.detail || 'No se pudo completar la radicación.', 'error');
      }
    });
  }

  verDetalleFaturaDian(factura: any) {
    this.http.get<any>(`${environment.apiUrl}/facturas/dian/${factura.id}`).subscribe({
      next: (res) => {
        this.facturaDianDetalle = res;
        this.mostrarModalDetalleDian = true;
        this.cd.detectChanges();
      },
      error: () => {
        // fallback: usar datos que ya tenemos
        this.facturaDianDetalle = factura;
        this.mostrarModalDetalleDian = true;
        this.cd.detectChanges();
      }
    });
  }

  // =====================================================================
  // T4.4.3 — Dividir PDF por rango de páginas
  // =====================================================================

  abrirModalDividirPdf(radicado: any) {
    this.radicadoPdfActual = radicado;
    this.infoPdf = null;
    this.cargandoInfoPdf = true;
    this.mostrarModalDividirPdf = true;
    this.pdfPaginaInicio = 1;
    this.pdfPaginaFin = 1;

    this.http.get<any>(`${environment.apiUrl}/radicados/${radicado.id}/pdf-info`).subscribe({
      next: (info) => {
        this.infoPdf = info;
        this.pdfPaginaFin = info.num_paginas || 1;
        this.cargandoInfoPdf = false;
        this.cd.detectChanges();
      },
      error: (err) => {
        this.cargandoInfoPdf = false;
        this.mostrarModalDividirPdf = false;
        Swal.fire('Error', err.error?.detail || 'No se pudo obtener información del PDF', 'error');
      }
    });
  }

  ejecutarDividirPdf() {
    if (!this.radicadoPdfActual) return;
    if (this.pdfPaginaInicio < 1 || this.pdfPaginaFin < this.pdfPaginaInicio) {
      Swal.fire('Rango inválido', 'Verifica los números de página ingresados.', 'warning');
      return;
    }

    const body = { pagina_inicio: this.pdfPaginaInicio, pagina_fin: this.pdfPaginaFin };

    Swal.fire({ title: 'Extrayendo páginas...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

    this.http.post(
      `${environment.apiUrl}/radicados/${this.radicadoPdfActual.id}/dividir-pdf`,
      body,
      { responseType: 'blob' }
    ).subscribe({
      next: (blob) => {
        Swal.close();
        const nro = this.radicadoPdfActual.nro_radicado || 'doc';
        const nombreArchivo = `${nro}_p${String(this.pdfPaginaInicio).padStart(3,'0')}-${String(this.pdfPaginaFin).padStart(3,'0')}.pdf`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nombreArchivo;
        a.click();
        URL.revokeObjectURL(url);
        this.mostrarModalDividirPdf = false;
        Swal.fire('¡Listo!', `Se extrajeron las páginas ${this.pdfPaginaInicio} a ${this.pdfPaginaFin} correctamente.`, 'success');
      },
      error: (err) => {
        Swal.close();
        Swal.fire('Error', err.error?.detail || 'No se pudo dividir el PDF', 'error');
      }
    });
  }

  cerrarModalDividirPdf() {
    this.mostrarModalDividirPdf = false;
    this.infoPdf = null;
    this.radicadoPdfActual = null;
  }

  cargarInformes() {
    this.informesCargando = true;
    const p: any = {};
    if (this.filtrosInformes.fecha_desde) p['fecha_desde'] = this.filtrosInformes.fecha_desde;
    if (this.filtrosInformes.fecha_hasta) p['fecha_hasta'] = this.filtrosInformes.fecha_hasta;
    if (this.filtrosInformes.tipo)        p['tipo']        = this.filtrosInformes.tipo;
    if (this.filtrosInformes.dependencia) p['dependencia'] = this.filtrosInformes.dependencia;

    this.http.get<any>(`${this.apiUrl}/admin/stats-informes`, { params: p }).subscribe({
      next: (res) => {
        this.informesResumen = res.resumen;
        this.informesCargando = false;
        this.informesListas = true;
        this.informesPeriodo = this.filtrosInformes.fecha_desde && this.filtrosInformes.fecha_hasta
          ? `${this.filtrosInformes.fecha_desde} al ${this.filtrosInformes.fecha_hasta}`
          : 'Últimos 12 meses';
        this.cd.detectChanges();
        setTimeout(() => { this._dibujarInformes(res); }, 50);
      },
      error: () => { this.informesCargando = false; }
    });
  }

  private _dibujarInformes(data: any) {
    const paleta = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b', '#06b6d4', '#f97316'];

    // --- Línea: tendencia mensual ---
    if (this.chartLineaRef?.nativeElement) {
      if (this.chartLinea) this.chartLinea.destroy();
      this.chartLinea = new Chart(this.chartLineaRef.nativeElement, {
        type: 'line',
        data: {
          labels: data.tendencia.labels,
          datasets: [{
            label: 'Radicados',
            data: data.tendencia.values,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,0.1)',
            tension: 0.4,
            fill: true,
            pointRadius: 4,
            pointBackgroundColor: '#3b82f6'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 } }, grid: { color: '#f1f5f9' } }
          }
        }
      });
    }

    // --- Dona: por tipo ---
    if (this.chartTipoRef?.nativeElement) {
      if (this.chartTipoPie) this.chartTipoPie.destroy();
      this.chartTipoPie = new Chart(this.chartTipoRef.nativeElement, {
        type: 'doughnut',
        data: {
          labels: data.por_tipo.labels,
          datasets: [{
            data: data.por_tipo.values,
            backgroundColor: paleta.slice(0, data.por_tipo.labels.length),
            borderWidth: 2, borderColor: '#fff'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
          cutout: '60%'
        }
      });
    }

    // --- Barras horizontales: ANS por dependencia ---
    if (this.chartAnsDepRef?.nativeElement) {
      if (this.chartAnsDep) this.chartAnsDep.destroy();
      this.chartAnsDep = new Chart(this.chartAnsDepRef.nativeElement, {
        type: 'bar',
        data: {
          labels: data.ans_dependencia.labels,
          datasets: [{
            label: '% Cumplimiento ANS',
            data: data.ans_dependencia.values,
            backgroundColor: data.ans_dependencia.values.map((v: number) =>
              v >= 80 ? '#16a34a' : v >= 60 ? '#f59e0b' : '#ef4444'),
            borderRadius: 4,
            borderSkipped: false as const
          }]
        },
        options: {
          indexAxis: 'y' as const,
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, max: 100, ticks: { callback: (v: any) => v + '%', font: { size: 10 } }, grid: { color: '#f1f5f9' } },
            y: { grid: { display: false }, ticks: { font: { size: 10 } } }
          }
        }
      });
    }
  }

  exportarInformesExcel() {
    const datos = this.informesResumen.map(r => ({
      'N° Radicado':      r.nro_radicado,
      'Tipo':             r.tipo_radicado,
      'Remitente/Origen': r.nombre_razon_social,
      'Asunto':           r.asunto,
      'Serie':            r.serie,
      'Dependencia':      r.seccion_responsable,
      'Estado':           r.estado,
      'Fecha Radicación': r.fecha_radicacion,
      'Fecha Vencimiento': r.fecha_vencimiento || 'Sin plazo'
    }));

    const ws = XLSX.utils.json_to_sheet(datos);
    ws['!cols'] = [14,12,30,40,20,25,15,20,18].map(w => ({ wch: w }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Radicados');
    const fecha = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `SIADE_Informe_${fecha}.xlsx`);
  }

  ngOnDestroy() {
    if (this.relojInterval) {
      clearInterval(this.relojInterval);
    }
    if (this.auditSubscription) {
      this.auditSubscription.unsubscribe();
    }
    if (this.chartBarras) { this.chartBarras.destroy(); }
    if (this.chartDona) { this.chartDona.destroy(); }
    if (this.chartLinea) { this.chartLinea.destroy(); }
    if (this.chartTipoPie) { this.chartTipoPie.destroy(); }
    if (this.chartAnsDep) { this.chartAnsDep.destroy(); }
  }
}
