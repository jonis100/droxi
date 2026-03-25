import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { SseService } from '../../services/sse.service';
import { Department, PatientRequest } from '../../models/patient-request.model';
import { DeptClassPipe } from '../../pipes/dept-class.pipe';
import { StatusClassPipe } from '../../pipes/status-class.pipe';

@Component({
  selector: 'app-request-list',
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatIconModule,
    MatSelectModule,
    MatFormFieldModule,
    FormsModule,
    DeptClassPipe,
    StatusClassPipe,
  ],
  templateUrl: './request-list.component.html',
  styleUrl: './request-list.component.scss',
})
export class RequestListComponent implements OnInit, OnDestroy {
  departments: Department[] = ['Dermatology', 'Radiology', 'Primary'];
  selectedDepartment: Department | '' = '';

  displayedColumns = ['patient_id', 'department', 'open_item_count', 'status', 'updated_at', 'expand'];
  requests = signal<PatientRequest[]>([]);
  total = signal(0);
  page = 1;
  pageSize = 20;

  expandedRequest = signal<PatientRequest | null>(null);

  private sseSub?: Subscription;

  constructor(
    private api: ApiService,
    private sse: SseService,
  ) {}

  ngOnInit(): void {
    this.loadRequests();
    this.subscribeSSE();
  }

  ngOnDestroy(): void {
    this.sseSub?.unsubscribe();
  }

  onDepartmentChange(): void {
    this.page = 1;
    this.expandedRequest.set(null);
    this.loadRequests();
    this.subscribeSSE();
  }

  loadRequests(): void {
    const dept = this.selectedDepartment || undefined;
    this.api.getRequests(dept, 'Open', this.page, this.pageSize).subscribe(res => {
      this.requests.set(res.items);
      this.total.set(res.total);
      const current = this.expandedRequest();
      if (current) {
        this.expandedRequest.set(res.items.find(r => r.id === current.id) ?? null);
      }
    });
  }

  toggleRow(row: PatientRequest): void {
    if (this.expandedRequest()?.id === row.id) {
      this.expandedRequest.set(null);
    } else {
      this.expandedRequest.set(row);
    }
  }

  onPageChange(event: PageEvent): void {
    this.page = event.pageIndex + 1;
    this.pageSize = event.pageSize;
    this.expandedRequest.set(null);
    this.loadRequests();
  }

  private subscribeSSE(): void {
    this.sseSub?.unsubscribe();
    const dept = this.selectedDepartment || undefined;
    this.sseSub = this.sse.connect(dept).subscribe(() => {
      this.loadRequests();
    });
  }
}
