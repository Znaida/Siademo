import { Component, OnInit, signal } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { RadicadoService } from './services/radicado';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.scss',
  standalone: false
})
export class App implements OnInit {
  public listaRadicados: any[] = [];
  public radicadosFiltrados: any[] = [];
  
  public formRadicacion = new FormGroup({
    asunto: new FormControl('', Validators.required),
    remitente: new FormControl('', Validators.required),
    archivo: new FormControl(null, Validators.required)
  });

  constructor(private radicadoService: RadicadoService) {}

  ngOnInit() {
    this.cargarTabla();
  }

  cargarTabla() {
    this.radicadoService.getRadicados().subscribe(datos => {
      this.listaRadicados = datos;
      this.radicadosFiltrados = datos; // Al cargar, ambas son iguales
    });
  }

  filtrar(termino: string) {
    if (!termino) {
      this.radicadosFiltrados = this.listaRadicados;
    } else {
      this.radicadosFiltrados = this.listaRadicados.filter(r => 
        r.asunto.toLowerCase().includes(termino.toLowerCase()) || 
        r.remitente.toLowerCase().includes(termino.toLowerCase()) ||
        r.numero.includes(termino)
      );
    }
  }

  // --- ESTA ES LA FUNCIÓN QUE TE FALTABA ---
  verArchivo(numero: string) {
    const url = `http://localhost:8000/descargar/${numero}`;
    window.open(url, '_blank');
  }

  enviarRadicado() {
    const formData = new FormData();
    formData.append('asunto', this.formRadicacion.get('asunto')?.value || '');
    formData.append('remitente', this.formRadicacion.get('remitente')?.value || '');
    formData.append('cliente_id', '1');
    formData.append('archivo', this.formRadicacion.get('archivo')?.value as any);

    this.radicadoService.crearRadicado(formData).subscribe(() => {
      alert('Radicado con éxito');
      this.formRadicacion.reset();
      this.cargarTabla();
    });
  }

  onFileSelect(event: any) {
    if (event.target.files.length > 0) {
      this.formRadicacion.patchValue({ archivo: event.target.files[0] });
    }
  }
}