import {
  Component, OnInit, OnDestroy, ElementRef, ViewChild,
  AfterViewInit, ChangeDetectorRef, NgZone
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface WorkflowTemplate {
  id?: number;
  nombre: string;
  descripcion: string;
  tipo: string;
  xml_content?: string;
  version?: number;
  activo?: number;
  es_default?: number;
  creado_en?: string;
  modificado_en?: string;
}

@Component({
  selector: 'app-bpmn-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="editor-wrapper">

  <!-- Panel izquierdo: lista de plantillas -->
  <div class="plantillas-panel">
    <div class="panel-header">
      <h3>Plantillas de Flujo</h3>
      <button class="btn-nueva" (click)="nuevaPlantilla()">+ Nueva</button>
    </div>

    <div class="plantilla-item"
         *ngFor="let p of plantillas"
         [class.activa]="plantillaActiva?.id === p.id"
         (click)="cargarPlantilla(p)">
      <div class="plantilla-info">
        <span class="plantilla-tipo" [class]="'tipo-' + p.tipo">{{ etiquetaTipo(p.tipo) }}</span>
        <span class="plantilla-nombre">{{ p.nombre }}</span>
        <span class="plantilla-version" *ngIf="p.version">v{{ p.version }}</span>
      </div>
      <span class="plantilla-default" *ngIf="p.es_default" title="Plantilla predeterminada">⭐</span>
    </div>

    <div class="sin-plantillas" *ngIf="plantillas.length === 0 && !cargandoLista">
      <p>No hay plantillas guardadas aún.</p>
      <small>Crea una nueva o carga una por defecto.</small>
    </div>
    <div class="cargando-lista" *ngIf="cargandoLista">Cargando...</div>
  </div>

  <!-- Panel derecho: editor -->
  <div class="editor-panel">

    <!-- Toolbar -->
    <div class="editor-toolbar" *ngIf="modoEditor">
      <div class="toolbar-meta">
        <input class="input-nombre" [(ngModel)]="formNombre" placeholder="Nombre de la plantilla" />
        <select class="select-tipo" [(ngModel)]="formTipo">
          <option value="entrada">📥 Comunicaciones Recibidas</option>
          <option value="salida">📤 Comunicaciones Enviadas</option>
          <option value="interna">🔄 Comunicaciones Internas</option>
          <option value="archivo">🗄️ Transferencia Archivo</option>
        </select>
        <input class="input-desc" [(ngModel)]="formDescripcion" placeholder="Descripción (opcional)" />
      </div>
      <div class="toolbar-acciones">
        <button class="btn-ajustar" (click)="ajustarVista()" title="Centrar diagrama">⊞</button>
        <button class="btn-cancelar" (click)="cancelarEdicion()">Cancelar</button>
        <button class="btn-guardar" (click)="guardar()" [disabled]="guardando">
          {{ guardando ? 'Guardando...' : (plantillaActiva?.id ? '💾 Actualizar' : '💾 Guardar') }}
        </button>
        <button class="btn-eliminar"
                *ngIf="plantillaActiva?.id && !plantillaActiva?.es_default"
                (click)="eliminar()">🗑️ Eliminar</button>
      </div>
    </div>

    <!-- Mensaje bienvenida -->
    <div class="editor-bienvenida" *ngIf="!modoEditor">
      <div class="bienvenida-content">
        <span class="bienvenida-icono">🌿</span>
        <h3>Editor de Flujos BPMN</h3>
        <p>Selecciona una plantilla de la lista para editarla,<br>o crea una nueva desde cero.</p>
        <div class="bienvenida-tips">
          <div class="tip"><strong>Drag & Drop</strong> — Arrastra nodos desde el panel lateral</div>
          <div class="tip"><strong>Conectar</strong> — Hover sobre un nodo y arrastra la flecha</div>
          <div class="tip"><strong>Editar</strong> — Doble clic sobre cualquier elemento</div>
        </div>
      </div>
    </div>

    <!-- Canvas BPMN -->
    <div class="bpmn-modeler-container" [class.visible]="modoEditor">
      <div #modelerContainer class="modeler-canvas"></div>
    </div>

    <!-- Error -->
    <div class="editor-error" *ngIf="error">⚠️ {{ error }}</div>
  </div>

</div>
  `,
  styles: [`
    .editor-wrapper {
      display: flex;
      height: calc(100vh - 140px);
      min-height: 600px;
      gap: 0;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      overflow: hidden;
      background: #fff;
    }

    /* Panel izquierdo */
    .plantillas-panel {
      width: 260px;
      min-width: 260px;
      border-right: 1px solid #e2e8f0;
      display: flex;
      flex-direction: column;
      background: #f8fafc;
    }
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      border-bottom: 1px solid #e2e8f0;
    }
    .panel-header h3 { margin: 0; font-size: 14px; font-weight: 600; color: #1e293b; }
    .btn-nueva {
      background: #2563eb; color: #fff; border: none;
      padding: 6px 12px; border-radius: 6px; font-size: 12px;
      cursor: pointer; font-weight: 600;
    }
    .btn-nueva:hover { background: #1d4ed8; }

    .plantilla-item {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 16px; cursor: pointer; border-bottom: 1px solid #f1f5f9;
      transition: background 0.15s;
    }
    .plantilla-item:hover { background: #eff6ff; }
    .plantilla-item.activa { background: #dbeafe; border-left: 3px solid #2563eb; }
    .plantilla-info { display: flex; flex-direction: column; gap: 2px; }
    .plantilla-tipo {
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      padding: 2px 6px; border-radius: 4px; width: fit-content;
    }
    .tipo-entrada { background: #dbeafe; color: #1d4ed8; }
    .tipo-salida  { background: #dcfce7; color: #15803d; }
    .tipo-interna { background: #ede9fe; color: #6d28d9; }
    .tipo-archivo { background: #fef3c7; color: #92400e; }
    .plantilla-nombre { font-size: 13px; color: #334155; font-weight: 500; }
    .plantilla-version { font-size: 11px; color: #94a3b8; }
    .plantilla-default { font-size: 14px; }
    .sin-plantillas { padding: 24px 16px; text-align: center; color: #94a3b8; font-size: 13px; }
    .cargando-lista { padding: 16px; text-align: center; color: #94a3b8; font-size: 13px; }

    /* Panel derecho */
    .editor-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Toolbar */
    .editor-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      border-bottom: 1px solid #e2e8f0;
      background: #f8fafc;
      gap: 12px;
      flex-wrap: wrap;
    }
    .toolbar-meta { display: flex; gap: 8px; flex: 1; flex-wrap: wrap; }
    .toolbar-acciones { display: flex; gap: 8px; align-items: center; }
    .input-nombre {
      padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px;
      font-size: 13px; width: 200px;
    }
    .select-tipo {
      padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px;
      font-size: 13px; background: #fff;
    }
    .input-desc {
      padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px;
      font-size: 13px; flex: 1; min-width: 150px;
    }
    .btn-ajustar {
      background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 10px;
      border-radius: 6px; cursor: pointer; font-size: 16px;
    }
    .btn-guardar {
      background: #16a34a; color: #fff; border: none;
      padding: 7px 16px; border-radius: 6px; font-size: 13px;
      cursor: pointer; font-weight: 600;
    }
    .btn-guardar:disabled { background: #86efac; cursor: not-allowed; }
    .btn-cancelar {
      background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;
      padding: 7px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
    }
    .btn-eliminar {
      background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
      padding: 7px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
    }

    /* Canvas */
    .bpmn-modeler-container {
      flex: 1;
      display: none;
      overflow: hidden;
    }
    .bpmn-modeler-container.visible { display: flex; }
    .modeler-canvas {
      width: 100%;
      height: 100%;
    }
    /* Estilos internos del modeler */
    .modeler-canvas :global(.djs-container) { background: #fafafa; }

    /* Bienvenida */
    .editor-bienvenida {
      flex: 1; display: flex; align-items: center; justify-content: center;
    }
    .bienvenida-content {
      text-align: center; max-width: 400px; padding: 32px;
    }
    .bienvenida-icono { font-size: 48px; display: block; margin-bottom: 16px; }
    .bienvenida-content h3 { color: #1e293b; margin-bottom: 8px; }
    .bienvenida-content p { color: #64748b; line-height: 1.6; margin-bottom: 24px; }
    .bienvenida-tips { display: flex; flex-direction: column; gap: 8px; }
    .tip {
      background: #f1f5f9; padding: 10px 16px; border-radius: 8px;
      font-size: 13px; color: #475569; text-align: left;
    }
    .tip strong { color: #1e293b; }

    /* Error */
    .editor-error {
      padding: 12px 16px; background: #fef2f2; color: #dc2626;
      border-top: 1px solid #fecaca; font-size: 13px;
    }

    /* bpmn-js toolbar override — aplicado globalmente desde dashboard.scss */
  `]
})
export class BpmnEditorComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('modelerContainer') modelerContainer!: ElementRef;

  plantillas: WorkflowTemplate[] = [];
  plantillaActiva: WorkflowTemplate | null = null;
  modoEditor = false;
  cargandoLista = false;
  guardando = false;
  error = '';

  formNombre = '';
  formTipo = 'entrada';
  formDescripcion = '';

  private modeler: any = null;
  private apiUrl = environment.apiUrl;

  // XMLs predeterminados por tipo
  private xmlDefaults: Record<string, string> = {
    entrada: '/bpmn/radicacion-entrada.bpmn',
    salida: '/bpmn/radicacion-salida.bpmn',
    interna: '/bpmn/comunicacion-interna.bpmn',
    archivo: '/bpmn/transferencia-archivo.bpmn',
  };

  constructor(private http: HttpClient, private cd: ChangeDetectorRef, private zone: NgZone) {}

  ngOnInit() { this.cargarLista(); }

  ngAfterViewInit() {}

  ngOnDestroy() { this.destruirModeler(); }

  get headers() {
    const token = localStorage.getItem('token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  etiquetaTipo(tipo: string): string {
    const map: Record<string, string> = {
      entrada: '📥 Recibida', salida: '📤 Enviada',
      interna: '🔄 Interna', archivo: '🗄️ Archivo'
    };
    return map[tipo] || tipo;
  }

  cargarLista() {
    this.cargandoLista = true;
    this.http.get<WorkflowTemplate[]>(`${this.apiUrl}/admin/workflows`, { headers: this.headers })
      .subscribe({
        next: (data) => { this.plantillas = data; this.cargandoLista = false; this.cd.detectChanges(); },
        error: () => { this.cargandoLista = false; this.cd.detectChanges(); }
      });
  }

  async cargarPlantilla(p: WorkflowTemplate) {
    if (!p.id) return;
    this.error = '';
    this.http.get<WorkflowTemplate>(`${this.apiUrl}/admin/workflows/${p.id}`, { headers: this.headers })
      .subscribe({
        next: async (data) => {
          this.plantillaActiva = data;
          this.formNombre = data.nombre;
          this.formTipo = data.tipo;
          this.formDescripcion = data.descripcion || '';
          this.modoEditor = true;
          this.cd.detectChanges();
          await this.inicializarModeler(data.xml_content!);
        },
        error: () => { this.error = 'No se pudo cargar la plantilla'; }
      });
  }

  async nuevaPlantilla() {
    this.plantillaActiva = null;
    this.formNombre = '';
    this.formTipo = 'entrada';
    this.formDescripcion = '';
    this.modoEditor = true;
    this.error = '';
    this.cd.detectChanges();
    // Cargar XML base del tipo seleccionado
    const xmlUrl = this.xmlDefaults[this.formTipo];
    const response = await fetch(xmlUrl);
    const xml = await response.text();
    await this.inicializarModeler(xml);
  }

  async inicializarModeler(xml: string) {
    await new Promise(r => setTimeout(r, 80));
    this.destruirModeler();
    const container = this.modelerContainer?.nativeElement;
    if (!container) return;

    // Dynamic import para evitar crash en arranque de Angular
    const { default: BpmnModeler } = await import('bpmn-js/lib/Modeler');
    this.modeler = new (BpmnModeler as any)({ container });
    try {
      await this.modeler.importXML(xml);
      this.modeler.get('canvas').zoom('fit-viewport', 'auto');
    } catch (e: any) {
      this.error = 'Error al cargar el diagrama: ' + e.message;
    }
    this.cd.detectChanges();
  }

  ajustarVista() {
    if (this.modeler) this.modeler.get('canvas').zoom('fit-viewport', 'auto');
  }

  async guardar() {
    if (!this.formNombre.trim()) { this.error = 'El nombre es obligatorio'; return; }
    this.guardando = true;
    this.error = '';

    try {
      const { xml } = await this.modeler.saveXML({ format: true });
      const body = {
        nombre: this.formNombre.trim(),
        tipo: this.formTipo,
        descripcion: this.formDescripcion.trim(),
        xml_content: xml
      };

      if (this.plantillaActiva?.id) {
        this.http.put(`${this.apiUrl}/admin/workflows/${this.plantillaActiva.id}`, body, { headers: this.headers })
          .subscribe({
            next: (res: any) => {
              this.guardando = false;
              this.plantillaActiva!.version = res.version;
              this.cargarLista();
              this.cd.detectChanges();
            },
            error: (e) => { this.guardando = false; this.error = e.error?.detail || 'Error al guardar'; this.cd.detectChanges(); }
          });
      } else {
        this.http.post<any>(`${this.apiUrl}/admin/workflows`, body, { headers: this.headers })
          .subscribe({
            next: (res) => {
              this.guardando = false;
              this.plantillaActiva = { ...body, id: res.id, version: 1, es_default: 0 };
              this.cargarLista();
              this.cd.detectChanges();
            },
            error: (e) => { this.guardando = false; this.error = e.error?.detail || 'Error al guardar'; this.cd.detectChanges(); }
          });
      }
    } catch (e: any) {
      this.guardando = false;
      this.error = 'Error al exportar el XML: ' + e.message;
    }
  }

  eliminar() {
    if (!this.plantillaActiva?.id || !confirm(`¿Eliminar "${this.plantillaActiva.nombre}"?`)) return;
    this.http.delete(`${this.apiUrl}/admin/workflows/${this.plantillaActiva.id}`, { headers: this.headers })
      .subscribe({
        next: () => { this.cancelarEdicion(); this.cargarLista(); },
        error: (e) => { this.error = e.error?.detail || 'Error al eliminar'; }
      });
  }

  cancelarEdicion() {
    this.modoEditor = false;
    this.plantillaActiva = null;
    this.error = '';
    this.destruirModeler();
    this.cd.detectChanges();
  }

  private destruirModeler() {
    if (this.modeler) { this.modeler.destroy(); this.modeler = null; }
  }
}
