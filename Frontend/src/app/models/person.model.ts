export type Gender = 'male' | 'female' | 'other';
export type PrivacyLevel = 'public' | 'family' | 'private';

export interface Person {
  id: string;
  first_name: string;
  last_name: string;
  maiden_name?: string | null;
  gender?: Gender | null;
  birth_date?: string | null;
  birth_place?: string | null;
  death_date?: string | null;
  death_place?: string | null;
  is_living: boolean;
  biography?: string | null;
  occupation?: string | null;
  nationality?: string | null;
  privacy_level: PrivacyLevel;
  main_photo_key?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonListResponse {
  items: Person[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface PersonCreate {
  first_name: string;
  last_name: string;
  maiden_name?: string;
  gender?: Gender;
  birth_date?: string;
  birth_place?: string;
  death_date?: string;
  death_place?: string;
  is_living?: boolean;
  biography?: string;
  occupation?: string;
  nationality?: string;
  privacy_level?: PrivacyLevel;
}

export type PersonUpdate = Partial<PersonCreate>;
