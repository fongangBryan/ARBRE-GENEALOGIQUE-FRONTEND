import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Filiation, FiliationCreate, FiliationUpdate } from '../models/filiation.model';

const API = 'http://localhost:8090/api/v1';

@Injectable({ providedIn: 'root' })
export class FiliationService {
  private http = inject(HttpClient);

  getParents(personId: string) {
    return this.http.get<Filiation[]>(`${API}/filiations/person/${personId}/parents`);
  }

  getChildren(personId: string) {
    return this.http.get<Filiation[]>(`${API}/filiations/person/${personId}/children`);
  }

  getById(id: string) {
    return this.http.get<Filiation>(`${API}/filiations/${id}`);
  }

  create(data: FiliationCreate) {
    return this.http.post<Filiation>(`${API}/filiations/`, data);
  }

  update(id: string, data: FiliationUpdate) {
    return this.http.put<Filiation>(`${API}/filiations/${id}`, data);
  }

  delete(id: string) {
    return this.http.delete<void>(`${API}/filiations/${id}`);
  }
}

