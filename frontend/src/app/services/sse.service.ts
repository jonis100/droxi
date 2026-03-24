import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';
import { Department } from '../models/patient-request.model';

export interface SSEUpdateEvent {
  event: string;
  request_ids: string[];
}

@Injectable({ providedIn: 'root' })
export class SseService {
  private baseUrl = '/api';

  constructor(private zone: NgZone) {}

  connect(department?: Department): Observable<SSEUpdateEvent> {
    return new Observable(observer => {
      let url = `${this.baseUrl}/events/updates`;
      if (department) {
        url += `?department=${department}`;
      }
      const eventSource = new EventSource(url);

      eventSource.addEventListener('update', (event: MessageEvent) => {
        this.zone.run(() => {
          try {
            const data = JSON.parse(event.data) as SSEUpdateEvent;
            observer.next(data);
          } catch {
            // Ignore parse errors from ping events
          }
        });
      });

      eventSource.onerror = () => {
        // EventSource auto-reconnects on error
      };

      return () => {
        eventSource.close();
      };
    });
  }
}
