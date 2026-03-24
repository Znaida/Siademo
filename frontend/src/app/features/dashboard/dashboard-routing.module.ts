import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Dashboard } from '../../components/dashboard/dashboard';
import { UsuariosLista } from '../../admin/usuarios-lista/usuarios-lista';
import { authGuard } from '../../guards/auth.guard';

const routes: Routes = [
  {
    path: '',
    component: Dashboard,
    canActivate: [authGuard]
  },
  {
    path: 'usuarios',
    component: UsuariosLista,
    canActivate: [authGuard]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class DashboardRoutingModule { }
