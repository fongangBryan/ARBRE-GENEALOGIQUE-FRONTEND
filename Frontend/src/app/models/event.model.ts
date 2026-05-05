export type EventType =
  | 'birth' | 'death' | 'baptism' | 'burial'
  | 'education' | 'employment' | 'residence' | 'custom';

export interface LifeEvent {
  id: string;
  person_id: string;
  event_type: EventType;
  date_start?: string | null;
  date_end?: string | null;
  place?: string | null;
  description?: string | null;
  meta?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LifeEventCreate {
  person_id: string;
  event_type: EventType;
  date_start?: string;
  date_end?: string;
  place?: string;
  description?: string;
  meta?: Record<string, unknown>;
}

export type LifeEventUpdate = Partial<Omit<LifeEventCreate, 'person_id'>>;
