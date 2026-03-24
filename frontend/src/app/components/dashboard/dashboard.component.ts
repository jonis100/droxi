import { Component } from '@angular/core';
import { RequestListComponent } from '../request-list/request-list.component';

@Component({
  selector: 'app-dashboard',
  imports: [RequestListComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {}
