import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/issues', pathMatch: 'full' },
  {
    path: 'issues',
    loadComponent: () =>
      import('./features/issues/containers/issue-list/issue-list.component')
        .then(m => m.IssueListComponent),
  },
  {
    path: 'issues/new',
    loadComponent: () =>
      import('./features/issues/containers/issue-form/issue-form.component')
        .then(m => m.IssueFormComponent),
  },
  {
    path: 'issues/edit/:id',
    loadComponent: () =>
      import('./features/issues/containers/issue-form/issue-form.component')
        .then(m => m.IssueFormComponent),
  },
  { path: '**', redirectTo: '/issues' },
];
