import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Issue, IssuePage, CreateIssueDto, UpdateIssueDto } from '../models/issue.model';

@Injectable({ providedIn: 'root' })
export class IssueService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/issues`;

  getAll(page: number = 1, pageSize: number = 20): Observable<IssuePage> {
    const params = new HttpParams()
      .set('page', page)
      .set('page_size', pageSize);
    return this.http.get<IssuePage>(this.apiUrl, { params });
  }

  getById(id: number): Observable<Issue> {
    return this.http.get<Issue>(`${this.apiUrl}/${id}`);
  }

  create(data: CreateIssueDto): Observable<Issue> {
    return this.http.post<Issue>(this.apiUrl, data);
  }

  update(id: number, data: UpdateIssueDto): Observable<Issue> {
    return this.http.put<Issue>(`${this.apiUrl}/${id}`, data);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
