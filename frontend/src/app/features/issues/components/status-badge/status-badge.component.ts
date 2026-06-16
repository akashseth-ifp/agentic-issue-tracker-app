import { Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';
import { IssueStatus } from '../../../../core/models/issue.model';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [NgClass],
  template: `<span [ngClass]="badgeClass">{{ status }}</span>`,
  styleUrl: './status-badge.component.scss',
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: IssueStatus;

  get badgeClass(): string {
    return {
      [IssueStatus.OPEN]: 'badge badge--open',
      [IssueStatus.IN_PROGRESS]: 'badge badge--in-progress',
      [IssueStatus.CLOSED]: 'badge badge--closed',
    }[this.status];
  }
}
