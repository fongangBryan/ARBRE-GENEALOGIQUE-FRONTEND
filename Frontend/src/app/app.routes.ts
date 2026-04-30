import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },

  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login').then(m => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () => import('./features/auth/register/register').then(m => m.RegisterComponent),
  },
  {
    path: 'verify-2fa',
    loadComponent: () => import('./features/auth/two-factor/two-factor').then(m => m.TwoFactorComponent),
  },

  {
    path: 'dashboard',
    canActivate: [authGuard, roleGuard(['editor', 'reader'])],
    loadComponent: () => import('./features/dashboard/dashboard').then(m => m.DashboardComponent),
  },

  {
    path: 'admin',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/admin/dashboard/admin-dashboard').then(m => m.AdminDashboardComponent),
  },

  { path: '**', redirectTo: 'login' },
];
