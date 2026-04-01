import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { Dashboard } from '../../components/dashboard/dashboard';
import { FlujosBpmnComponent } from '../../components/flujos/flujos';
import { BpmnEditorComponent } from '../../components/flujos/bpmn-editor';
import { UsuariosLista } from '../../admin/usuarios-lista/usuarios-lista';
import { DashboardRoutingModule } from './dashboard-routing.module';

@NgModule({
  declarations: [Dashboard],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    FlujosBpmnComponent,   // standalone
    BpmnEditorComponent,   // standalone — T8.2 editor drag & drop
    UsuariosLista,         // standalone
    DashboardRoutingModule
  ]
})
export class DashboardModule { }
