import { Pipe, PipeTransform } from '@angular/core';
import { Department } from '../models/patient-request.model';

const DEPT_CLASSES: Record<Department, string> = {
  Dermatology: 'dept-dermatology',
  Radiology: 'dept-radiology',
  Primary: 'dept-primary',
};

@Pipe({ name: 'deptClass', standalone: true, pure: true })
export class DeptClassPipe implements PipeTransform {
  transform(department: Department): string {
    return DEPT_CLASSES[department] ?? '';
  }
}
