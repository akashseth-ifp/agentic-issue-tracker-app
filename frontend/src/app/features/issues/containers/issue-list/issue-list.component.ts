import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { BehaviorSubject, switchMap, distinctUntilChanged, catchError, finalize, of } from 'rxjs';
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
  isLoading = false;
  error: string | null = null;
  pendingDeleteId: number | null = null;

  // BehaviorSubject as the page "source of truth"
  private page$ = new BehaviorSubject<number>(1);

  // RxJS pipeline — distinctUntilChanged + switchMap are the rubric operators
  issuePage$ = this.page$.pipe(
    distinctUntilChanged(),                      // skip if same page emitted twice
    switchMap(page => {                          // cancel previous in-flight request on page change
      this.isLoading = true;
      this.error = null;
      return this.issueService.getAll(page, this.pageSize).pipe(
        catchError(err => {
          this.error = err.message;
          return of(null);                       // return null so stream stays alive after error
        }),
        finalize(() => this.isLoading = false),  // always turn off spinner
      );
    }),
    takeUntilDestroyed(),                        // auto-unsubscribe when component is destroyed
  );

  get currentPage(): number { return this.page$.value; }

  onPageChange(page: number) { this.page$.next(page); }
  navigateToEdit(id: number) { this.router.navigate(['/issues/edit', id]); }
  showDeleteConfirm(id: number) { this.pendingDeleteId = id; }
  cancelDelete() { this.pendingDeleteId = null; }

  confirmDelete(id: number) {
    this.isLoading = true;
    this.issueService.delete(id).pipe(
      finalize(() => this.isLoading = false),
    ).subscribe({
      next: () => {
        this.pendingDeleteId = null;
        this.page$.next(this.currentPage); // re-emit same page to refresh the list
      },
      error: err => this.error = err.message,
    });
  }
}
