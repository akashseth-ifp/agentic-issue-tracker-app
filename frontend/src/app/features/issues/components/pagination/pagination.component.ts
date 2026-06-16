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
  get pages(): number[] { return Array.from({ length: this.totalPages }, (_, i) => i + 1); }

  prev() { if (this.hasPrev) this.pageChange.emit(this.currentPage - 1); }
  next() { if (this.hasNext) this.pageChange.emit(this.currentPage + 1); }
  goTo(page: number) { this.pageChange.emit(page); }
}
