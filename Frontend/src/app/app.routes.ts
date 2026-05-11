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
    path: 'auth/forgot-password',
    loadComponent: () => import('./features/auth/forgot-password/forgot-password').then(m => m.ForgotPasswordComponent),
  },
  {
    path: 'auth/reset-password',
    loadComponent: () => import('./features/auth/reset-password/reset-password').then(m => m.ResetPasswordComponent),
  },
  {
    path: 'auth/verify-email',
    loadComponent: () => import('./features/auth/verify-email/verify-email').then(m => m.VerifyEmailComponent),
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

  {
    path: 'members',
    canActivate: [authGuard],
    loadComponent: () => import('./features/persons/persons').then(m => m.PersonsComponent),
  },

  {
    path: 'members/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/persons/person-detail/person-detail').then(m => m.PersonDetailComponent),
  },

  {
    path: 'tree',
    canActivate: [authGuard],
    loadComponent: () => import('./features/tree/tree').then(m => m.TreeComponent),
  },

  {
    path: 'settings',
    canActivate: [authGuard],
    loadComponent: () => import('./features/settings/settings').then(m => m.SettingsComponent),
  },

  {
    path: 'unions',
    canActivate: [authGuard, roleGuard(['editor', 'admin'])],
    loadComponent: () => import('./features/unions/unions').then(m => m.UnionsComponent),
  },

  {
    path: 'media',
    canActivate: [authGuard, roleGuard(['editor', 'admin'])],
    loadComponent: () => import('./features/media/media').then(m => m.MediaComponent),
  },

  { path: '**', redirectTo: 'login' },
];
