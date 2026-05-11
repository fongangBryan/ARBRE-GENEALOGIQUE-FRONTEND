export interface Tag {
  id: string;
  label: string;
  description?: string | null;
  color: string;
  icon?: string | null;
  created_by?: string | null;
  created_at?: string;
}

export interface TagCreate {
  label: string;
  description?: string;
  color?: string;
  icon?: string;
}

export interface TagUpdate {
  label?: string;
  description?: string;
  color?: string;
  icon?: string;
}

export interface TagListResponse {
  items: Tag[];
  total: number;
}
