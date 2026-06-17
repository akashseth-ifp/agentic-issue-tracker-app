import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ToastService {
  private message$ = new Subject<string>();

  readonly messages$ = this.message$.asObservable();

  show(message: string): void {
    this.message$.next(message);
  }
}
