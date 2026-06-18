import { Component, Output, EventEmitter, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { AssistantService } from '../../assistant.service';

@Component({
  selector: 'app-assistant-panel',
  standalone: true,
  templateUrl: './assistant-panel.component.html',
  styleUrl: './assistant-panel.component.scss',
})
export class AssistantPanelComponent {
  private assistantService = inject(AssistantService);

  @Output() issuesChanged = new EventEmitter<void>();

  isExpanded = signal(false);
  isLoading = signal(false);
  response = signal<string | null>(null);
  error = signal<string | null>(null);
  instruction = signal('');
  pendingCursor = signal<string | null>(null);

  togglePanel(): void {
    this.isExpanded.update(v => !v);
    if (!this.isExpanded()) {
      this.pendingCursor.set(null);
      this.response.set(null);
      this.error.set(null);
    }
  }

  closeOnBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('assistant-modal__backdrop')) {
      this.togglePanel();
    }
  }

  submit(): void {
    if (!this.instruction().trim() || this.isLoading()) return;
    this.isLoading.set(true);
    this.response.set(null);
    this.error.set(null);

    this.assistantService.run(this.instruction(), this.pendingCursor()).pipe(
      finalize(() => this.isLoading.set(false)),
    ).subscribe({
      next: (result) => {
        this.response.set(result.response);
        this.pendingCursor.set(result.next_cursor);
        if (result.mutations_made) {
          this.pendingCursor.set(null);
          this.issuesChanged.emit();
        }
      },
      error: (err) => {
        this.error.set(err.error?.detail || err.message || 'Assistant failed. Please try again.');
      },
    });
  }
}
