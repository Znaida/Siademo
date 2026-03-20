import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Login } from './components/login/login';
import { Dashboard } from './components/dashboard/dashboard';
import { UsuariosLista } from './admin/usuarios-lista/usuarios-lista'; // <--- Importamos el nuevo componente
import { authGuard } from './guards/auth.guard'; 

const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: Login },
  
  // Dashboard protegido
  { 
    path: 'dashboard', 
    component: Dashboard, 
    canActivate: [authGuard] 
  },

  // RUTA DE GESTIÓN JERÁRQUICA [Requisito 1.15]
  { 
    path: 'admin/usuarios', 
    component: UsuariosLista, 
    canActivate: [authGuard] // <--- El guardia también vigila la lista de cuentas
  },
  
  { path: '**', redirectTo: 'login' } 
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }