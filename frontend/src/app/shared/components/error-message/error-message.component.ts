import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-error-message',
  standalone: true,
  template: `<div class="error-banner">{{ message }}</div>`,
  styleUrl: './error-message.component.scss',
})
export class ErrorMessageComponent {
  @Input({ required: true }) message!: string;
}
