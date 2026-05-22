import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Union, UnionCreate, UnionUpdate } from '../models/union.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class UnionService {
  private http = inject(HttpClient);

  getByPerson(personId: string) {
    return this.http.get<Union[]>(`${API}/unions/person/${personId}`);
  }

  getById(id: string) {
    return this.http.get<Union>(`${API}/unions/${id}`);
  }

  create(data: UnionCreate) {
    return this.http.post<Union>(`${API}/unions`, data);
  }

  update(id: string, data: UnionUpdate) {
    return this.http.put<Union>(`${API}/unions/${id}`, data);
  }

  delete(id: string) {
    return this.http.delete<void>(`${API}/unions/${id}`);
  }
}

