import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  templateUrl: './toast.component.html',
  styleUrl: './toast.component.scss',
})
export class ToastComponent {
  private toastService = inject(ToastService);

  message = signal<string | null>(null);
  visible = signal(false);
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.toastService.messages$.pipe(takeUntilDestroyed()).subscribe(msg => {
      if (this.timer) clearTimeout(this.timer);
      this.message.set(msg);
      this.visible.set(true);
      this.timer = setTimeout(() => {
        this.visible.set(false);
        this.message.set(null);
      }, 3000);
    });
  }

  dismiss(): void {
    if (this.timer) clearTimeout(this.timer);
    this.visible.set(false);
    this.message.set(null);
  }
}
