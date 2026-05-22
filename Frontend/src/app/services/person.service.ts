import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Person, PersonCreate, PersonUpdate, PersonListResponse } from '../models/person.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class PersonService {
  private http = inject(HttpClient);

  list(page = 1, limit = 20, search?: string) {
    let params = new HttpParams().set('page', page).set('limit', limit);
    if (search?.trim()) params = params.set('search', search.trim());
    return this.http.get<PersonListResponse>(`${API}/persons/`, { params });
  }

  get(id: string) {
    return this.http.get<Person>(`${API}/persons/${id}`);
  }

  create(data: PersonCreate) {
    return this.http.post<Person>(`${API}/persons/`, data);
  }

  update(id: string, data: PersonUpdate) {
    return this.http.put<Person>(`${API}/persons/${id}`, data);
  }

  delete(id: string) {
    return this.http.delete<void>(`${API}/persons/${id}`);
  }
}

