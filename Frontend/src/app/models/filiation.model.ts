export type FiliationType = 'biological' | 'adoptive' | 'step' | 'guardian';

export interface Filiation {
  id: string;
  parent_id: string;
  child_id: string;
  filiation_type: FiliationType;
  created_at: string;
  updated_at: string;
}

export interface FiliationCreate {
  parent_id: string;
  child_id: string;
  filiation_type?: FiliationType;
}

export interface FiliationUpdate {
  filiation_type: FiliationType;
}
