import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { IssueService } from '../../../../core/services/issue.service';
import { IssueStatus, UpdateIssueDto, CreateIssueDto } from '../../../../core/models/issue.model';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-issue-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './issue-form.component.html',
  styleUrl: './issue-form.component.scss',
})
export class IssueFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private issueService = inject(IssueService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  readonly statusOptions = Object.values(IssueStatus);
  isEditMode = false;
  issueId: number | null = null;

  isFetching = signal(false);
  isSubmitting = signal(false);
  error = signal<string | null>(null);

  form = this.fb.group({
    title: ['', [Validators.required, Validators.maxLength(255)]],
    description: ['', Validators.maxLength(2000)],
    status: [IssueStatus.OPEN, Validators.required],
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    this.issueId = id ? Number(id) : null;
    this.isEditMode = !!this.issueId;

    if (this.isEditMode) {
      this.isFetching.set(true);
      this.issueService.getById(this.issueId!).pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isFetching.set(false)),
      ).subscribe({
        next: issue => this.form.patchValue(issue),
        error: err => this.error.set(err.message),
      });
    }
  }

  submit(): void {
    if (this.form.invalid) return;
    this.isSubmitting.set(true);
    this.error.set(null);

    const data = this.form.getRawValue();
    const request$ = this.isEditMode
      ? this.issueService.update(this.issueId!, data as UpdateIssueDto)
      : this.issueService.create(data as CreateIssueDto);

    request$.pipe(
      finalize(() => this.isSubmitting.set(false)),
    ).subscribe({
      next: () => this.router.navigate(['/issues']),
      error: err => this.error.set(err.message),
    });
  }

  get titleErrors() { return this.form.get('title')?.errors; }
  get isTitleInvalid() {
    const ctrl = this.form.get('title');
    return ctrl?.invalid && ctrl?.touched;
  }
}
