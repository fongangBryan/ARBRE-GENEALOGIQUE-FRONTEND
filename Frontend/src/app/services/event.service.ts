import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { LifeEvent, LifeEventCreate, LifeEventUpdate } from '../models/event.model';

const API = 'http://localhost:8090/api/v1';

@Injectable({ providedIn: 'root' })
export class EventService {
  private http = inject(HttpClient);

  getByPerson(personId: string) {
    return this.http.get<LifeEvent[]>(`${API}/events/person/${personId}`);
  }

  getTimeline(personId: string, startYear?: number, endYear?: number) {
    let params = new HttpParams();
    if (startYear != null) params = params.set('start_year', startYear);
    if (endYear   != null) params = params.set('end_year',   endYear);
    return this.http.get<LifeEvent[]>(`${API}/events/timeline/${personId}`, { params });
  }

  create(data: LifeEventCreate) {
    return this.http.post<LifeEvent>(`${API}/events/`, data);
  }

  update(id: string, data: LifeEventUpdate) {
    return this.http.put<LifeEvent>(`${API}/events/${id}`, data);
  }

  delete(id: string) {
    return this.http.delete<void>(`${API}/events/${id}`);
  }
}

