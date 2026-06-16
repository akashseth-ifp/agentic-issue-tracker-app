import { Component, Input, Output, EventEmitter } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Issue } from '../../../../core/models/issue.model';
import { StatusBadgeComponent } from '../status-badge/status-badge.component';

@Component({
  selector: 'app-issue-card',
  standalone: true,
  imports: [StatusBadgeComponent, DatePipe],
  templateUrl: './issue-card.component.html',
  styleUrl: './issue-card.component.scss',
})
export class IssueCardComponent {
  @Input({ required: true }) issue!: Issue;
  @Output() editClicked = new EventEmitter<number>();
  @Output() deleteClicked = new EventEmitter<number>();
}
