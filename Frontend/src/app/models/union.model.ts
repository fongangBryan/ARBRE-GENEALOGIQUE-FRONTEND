export type UnionType   = 'mariage' | 'union_libre' | 'pacs' | 'fiancailles';
export type UnionStatut = 'actif' | 'dissous';

export interface Union {
  id: string;
  person_id_1: string;
  person_id_2: string;
  union_type: UnionType;
  date_union?: string | null;
  lieu_union?: string | null;
  date_dissolution?: string | null;
  statut: UnionStatut;
  created_at: string;
  updated_at: string;
}

export interface UnionCreate {
  person_id_1: string;
  person_id_2: string;
  union_type: UnionType;
  date_union?: string;
  lieu_union?: string;
  date_dissolution?: string;
  statut?: UnionStatut;
}

export type UnionUpdate = Partial<Omit<UnionCreate, 'person_id_1' | 'person_id_2'>>;
