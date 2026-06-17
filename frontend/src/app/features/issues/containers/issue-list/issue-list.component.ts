import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { BehaviorSubject, Subject, merge, switchMap, distinctUntilChanged, catchError, finalize, of, map } from 'rxjs';
import { AsyncPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { IssueService } from '../../../../core/services/issue.service';
import { IssueCardComponent } from '../../components/issue-card/issue-card.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog/confirm-dialog.component';
import { PaginationComponent } from '../../components/pagination/pagination.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../../../../shared/components/error-message/error-message.component';

@Component({
  selector: 'app-issue-list',
  standalone: true,
  imports: [
    AsyncPipe,
    RouterLink,
    IssueCardComponent,
    ConfirmDialogComponent,
    PaginationComponent,
    LoadingSpinnerComponent,
    ErrorMessageComponent,
  ],
  templateUrl: './issue-list.component.html',
  styleUrl: './issue-list.component.scss',
})
export class IssueListComponent {
  private issueService = inject(IssueService);
  private router = inject(Router);

  readonly pageSize = 20;
  isLoading = signal(false);
  error = signal<string | null>(null);
  pendingDeleteId = signal<number | null>(null);

  private page$ = new BehaviorSubject<number>(1);
  private refresh$ = new Subject<void>();

  issuePage$ = merge(
    this.page$.pipe(distinctUntilChanged()),
    this.refresh$.pipe(map(() => this.page$.value)),
  ).pipe(
    switchMap(page => {
      this.isLoading.set(true);
      this.error.set(null);
      return this.issueService.getAll(page, this.pageSize).pipe(
        catchError(err => {
          this.error.set(err.message);
          return of(null);
        }),
        finalize(() => this.isLoading.set(false)),
      );
    }),
    takeUntilDestroyed(),
  );

  get currentPage(): number { return this.page$.value; }

  onPageChange(page: number) { this.page$.next(page); }
  navigateToEdit(id: number) { this.router.navigate(['/issues/edit', id]); }
  showDeleteConfirm(id: number) { this.pendingDeleteId.set(id); }
  cancelDelete() { this.pendingDeleteId.set(null); }

  confirmDelete(id: number) {
    this.isLoading.set(true);
    this.issueService.delete(id).pipe(
      finalize(() => this.isLoading.set(false)),
    ).subscribe({
      next: () => {
        this.pendingDeleteId.set(null);
        this.refresh$.next();
      },
      error: err => this.error.set(err.message),
    });
  }
}
