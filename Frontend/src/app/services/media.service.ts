import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { Media, MediaUploadResponse } from '../models/media.model';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class MediaService {
  private http = inject(HttpClient);

  getByOwner(ownerType: string, ownerId: string) {
    return this.http.get<Media[]>(`${API}/media/owner/${ownerType}/${ownerId}`);
  }

  upload(file: File, ownerType: string, ownerId: string): Observable<{ progress: number; result?: MediaUploadResponse }> {
    const form = new FormData();
    form.append('file', file);
    form.append('owner_type', ownerType);
    form.append('owner_id', ownerId);

    return this.http.post<MediaUploadResponse>(`${API}/media/upload`, form, {
      reportProgress: true,
      observe: 'events',
    }).pipe(
      map(event => {
        if (event.type === HttpEventType.UploadProgress) {
          const progress = Math.round(100 * (event.loaded / (event.total ?? event.loaded)));
          return { progress };
        }
        if (event.type === HttpEventType.Response) {
          return { progress: 100, result: event.body! };
        }
        return { progress: 0 };
      })
    );
  }

  delete(id: string) {
    return this.http.delete<void>(`${API}/media/${id}`);
  }

  mediaUrl(id: string)           { return `${API}/media/${id}`; }
  thumbnailUrl(id: string)       { return `${API}/media/${id}/thumbnail`; }
}

