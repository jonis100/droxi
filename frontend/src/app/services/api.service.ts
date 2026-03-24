import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Department, ItemStatus, PaginatedResponse, PatientRequest } from '../models/patient-request.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getRequests(
    department?: Department,
    status?: ItemStatus,
    page: number = 1,
    pageSize: number = 20
  ): Observable<PaginatedResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());

    if (department) params = params.set('department', department);
    if (status) params = params.set('status', status);

    return this.http.get<PaginatedResponse>(`${this.baseUrl}/requests`, { params });
  }

  getRequest(id: string): Observable<PatientRequest> {
    return this.http.get<PatientRequest>(`${this.baseUrl}/requests/${id}`);
  }
}
