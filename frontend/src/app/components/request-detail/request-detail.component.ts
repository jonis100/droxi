import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../services/api.service';
import { PatientRequest } from '../../models/patient-request.model';
import { DeptClassPipe } from '../../pipes/dept-class.pipe';
import { StatusClassPipe } from '../../pipes/status-class.pipe';

@Component({
  selector: 'app-request-detail',
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    DeptClassPipe,
    StatusClassPipe,
  ],
  templateUrl: './request-detail.component.html',
  styleUrl: './request-detail.component.scss',
})
export class RequestDetailComponent implements OnInit {
  request: PatientRequest | null = null;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.getRequest(id).subscribe({
      next: req => this.request = req,
      error: err => console.error('Failed to load request detail', err),
    });
  }
}
