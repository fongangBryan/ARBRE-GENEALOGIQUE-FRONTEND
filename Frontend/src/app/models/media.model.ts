export interface Media {
  id: string;
  filename?: string;
  storage_key: string;
  thumbnail_key?: string | null;
  url: string;
  thumbnail_url?: string | null;
  mime_type?: string | null;
  owner_type?: string;
  owner_id?: string;
  privacy_level?: string;
  created_at?: string;
}

export interface MediaUploadResponse {
  id: string;
  filename: string;
  storage_key: string;
  thumbnail_key?: string | null;
  url: string;
  thumbnail_url?: string | null;
  mime_type?: string | null;
}
