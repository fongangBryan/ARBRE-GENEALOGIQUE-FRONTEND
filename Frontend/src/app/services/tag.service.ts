import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Tag, TagCreate, TagUpdate, TagListResponse } from '../models/tag.model';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class TagService {
  private http = inject(HttpClient);

  list() {
    return this.http.get<TagListResponse>(`${API}/tags/`);
  }

  get(tagId: string) {
    return this.http.get<Tag>(`${API}/tags/${tagId}`);
  }

  create(data: TagCreate) {
    return this.http.post<Tag>(`${API}/tags/`, data);
  }

  update(tagId: string, data: TagUpdate) {
    return this.http.put<Tag>(`${API}/tags/${tagId}`, data);
  }

  delete(tagId: string) {
    return this.http.delete<void>(`${API}/tags/${tagId}`);
  }

  getPersonTags(personId: string) {
    return this.http.get<Tag[]>(`${API}/tags/person/${personId}`);
  }

  addTagToPerson(personId: string, tagId: string) {
    return this.http.post<void>(`${API}/tags/person/${personId}/${tagId}`, {});
  }

  removeTagFromPerson(personId: string, tagId: string) {
    return this.http.delete<void>(`${API}/tags/person/${personId}/${tagId}`);
  }
}
