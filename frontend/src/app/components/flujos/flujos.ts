import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit, ChangeDetectorRef, NgZone, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import BpmnViewer from 'bpmn-js';

interface Flujo {
  id: string;
  nombre: string;
  descripcion: string;
  archivo: string;
  color: string;
  icono: string;
}

export interface DatosFlujoRadicado {
  nro_radicado: string;
  estado: string;
  archivo_bpmn: string;
  paso_actual: string;
  pasos_completados: string[];
  todos_los_pasos: string[];
}

@Component({
  selector: 'app-flujos',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './flujos.html',
  styleUrls: ['./flujos.scss']
})
export class FlujosBpmnComponent implements OnInit, AfterViewInit, OnDestroy, OnChanges {
  @ViewChild('bpmnContainer') bpmnContainer!: ElementRef;

  // Si se pasan datos de un radicado específico, modo radicado
  @Input() datosFlujo: DatosFlujoRadicado | null = null;

  private viewer: any = null;

  constructor(private cd: ChangeDetectorRef, private zone: NgZone) {}

  flujos: Flujo[] = [
    {
      id: 'entrada',
      nombre: 'Comunicaciones Recibidas',
      descripcion: 'Desde que el ciudadano entrega el documento hasta su archivado y respuesta.',
      archivo: '/bpmn/radicacion-entrada.bpmn',
      color: '#2563eb',
      icono: '📥'
    },
    {
      id: 'salida',
      nombre: 'Comunicaciones Enviadas',
      descripcion: 'Desde la generación del documento hasta su envío y archivado.',
      archivo: '/bpmn/radicacion-salida.bpmn',
      color: '#16a34a',
      icono: '📤'
    },
    {
      id: 'interna',
      nombre: 'Comunicaciones Internas',
      descripcion: 'Memorandos y circulares entre dependencias de la Alcaldía.',
      archivo: '/bpmn/comunicacion-interna.bpmn',
      color: '#7c3aed',
      icono: '🔄'
    },
    {
      id: 'archivo',
      nombre: 'Transferencia al Archivo Central',
      descripcion: 'Proceso de transferencia documental primaria a Archivo Central.',
      archivo: '/bpmn/transferencia-archivo.bpmn',
      color: '#d97706',
      icono: '🗄️'
    }
  ];

  flujoActivo: Flujo = this.flujos[0];
  cargando: boolean = false;
  error: string = '';

  ngOnInit() {}

  ngAfterViewInit() {
    this.inicializarViewer();
    if (this.datosFlujo) {
      this.cargarFlujoRadicado(this.datosFlujo);
    } else {
      this.cargarFlujo(this.flujoActivo);
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['datosFlujo'] && this.viewer && this.datosFlujo) {
      this.cargarFlujoRadicado(this.datosFlujo);
    }
  }

  inicializarViewer() {
    if (this.viewer) {
      this.viewer.destroy();
    }
    this.viewer = new BpmnViewer({
      container: this.bpmnContainer.nativeElement
    });
  }

  async seleccionarFlujo(flujo: Flujo) {
    this.flujoActivo = flujo;
    await this.cargarFlujo(flujo);
  }

  async cargarFlujo(flujo: Flujo) {
    this.zone.run(() => { this.cargando = true; this.error = ''; this.cd.detectChanges(); });
    try {
      const response = await fetch(flujo.archivo);
      if (!response.ok) throw new Error('No se pudo cargar el archivo BPMN');
      const xml = await response.text();
      await this.viewer.importXML(xml);
      const canvas = this.viewer.get('canvas');
      canvas.zoom('fit-viewport', 'auto');
    } catch (e: any) {
      this.zone.run(() => { this.error = 'Error: ' + e.message; });
    } finally {
      this.zone.run(() => { this.cargando = false; this.cd.detectChanges(); });
    }
  }

  async cargarFlujoRadicado(datos: DatosFlujoRadicado) {
    this.zone.run(() => { this.cargando = true; this.error = ''; this.cd.detectChanges(); });
    try {
      const url = `/bpmn/${datos.archivo_bpmn}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('No se pudo cargar el diagrama BPMN');
      const xml = await response.text();
      await this.viewer.importXML(xml);
      const canvas = this.viewer.get('canvas');
      canvas.zoom('fit-viewport', 'auto');

      // Colorear nodos según estado
      this.colorearNodos(datos.pasos_completados, datos.paso_actual);
    } catch (e: any) {
      this.zone.run(() => { this.error = 'Error: ' + e.message; });
      console.error(e);
    } finally {
      this.zone.run(() => { this.cargando = false; this.cd.detectChanges(); });
    }
  }

  colorearNodos(completados: string[], actual: string) {
    const canvas = this.viewer.get('canvas');
    const elementRegistry = this.viewer.get('elementRegistry');

    elementRegistry.getAll().forEach((element: any) => {
      const id = element.id;
      // Limpiar marcadores previos
      canvas.removeMarker(id, 'nodo-completado');
      canvas.removeMarker(id, 'nodo-actual');
      canvas.removeMarker(id, 'nodo-pendiente');

      if (id === actual) {
        canvas.addMarker(id, 'nodo-actual');
      } else if (completados.includes(id)) {
        canvas.addMarker(id, 'nodo-completado');
      } else if (!id.startsWith('flujo') && !id.startsWith('BPMNDiagram') && !id.startsWith('BPMNPlane') && !id.includes('_di') && !id.includes('_label')) {
        canvas.addMarker(id, 'nodo-pendiente');
      }
    });
  }

  ajustarVista() {
    if (this.viewer) {
      const canvas = this.viewer.get('canvas');
      canvas.zoom('fit-viewport', 'auto');
    }
  }

  ngOnDestroy() {
    if (this.viewer) {
      this.viewer.destroy();
    }
  }
}
