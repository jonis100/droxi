import { Pipe, PipeTransform } from '@angular/core';
import { ItemStatus } from '../models/patient-request.model';

@Pipe({ name: 'statusClass', standalone: true, pure: true })
export class StatusClassPipe implements PipeTransform {
  transform(status: ItemStatus): string {
    return status === 'Closed' ? 'status-closed' : 'status-open';
  }
}
