export type Department = 'Dermatology' | 'Radiology' | 'Primary';
export type ItemStatus = 'Open' | 'Closed';

export interface InboxItem {
  id: string;
  external_id: string;
  patient_id: string;
  message_text: string | null;
  medications: string[] | null;
  department: Department;
  status: ItemStatus;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface PatientRequest {
  id: string;
  patient_id: string;
  department: Department;
  status: ItemStatus;
  open_item_count: number;
  created_at: string;
  updated_at: string;
  items?: InboxItem[];
}

export interface PaginatedResponse {
  items: PatientRequest[];
  total: number;
  page: number;
  page_size: number;
}
