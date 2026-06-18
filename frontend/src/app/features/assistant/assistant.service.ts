import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AssistantResponse {
  response: string;
  mutations_made: boolean;
  next_cursor: string | null;
}

@Injectable({ providedIn: 'root' })
export class AssistantService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/assistant`;

  run(instruction: string, cursor: string | null = null): Observable<AssistantResponse> {
    return this.http.post<AssistantResponse>(`${this.baseUrl}/run`, { instruction, cursor });
  }
}
