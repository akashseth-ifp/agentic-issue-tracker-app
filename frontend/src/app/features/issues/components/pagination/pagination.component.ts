import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [],
  templateUrl: './pagination.component.html',
  styleUrl: './pagination.component.scss',
})
export class PaginationComponent {
  @Input({ required: true }) currentPage!: number;
  @Input({ required: true }) totalPages!: number;
  @Input({ required: true }) total!: number;
  @Output() pageChange = new EventEmitter<number>();

  get hasPrev(): boolean { return this.currentPage > 1; }
  get hasNext(): boolean { return this.currentPage < this.totalPages; }

  /** Returns page numbers with null representing an ellipsis gap. */
  get visiblePages(): (number | null)[] {
    const { currentPage: c, totalPages: t } = this;
    if (t <= 7) {
      return Array.from({ length: t }, (_, i) => i + 1);
    }
    const anchors = new Set<number>([1, t]);
    for (let i = Math.max(1, c - 2); i <= Math.min(t, c + 2); i++) anchors.add(i);
    const sorted = Array.from(anchors).sort((a, b) => a - b);
    const result: (number | null)[] = [];
    let prev = 0;
    for (const p of sorted) {
      if (p - prev > 1) result.push(null);
      result.push(p);
      prev = p;
    }
    return result;
  }

  prev() { if (this.hasPrev) this.pageChange.emit(this.currentPage - 1); }
  next() { if (this.hasNext) this.pageChange.emit(this.currentPage + 1); }
  goTo(page: number) { this.pageChange.emit(page); }
}
