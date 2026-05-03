export type FileRecord = {
  file_id: string;
  filename: string;
  created_at?: string;
  status?: string;
  size_bytes?: number;
};

export type EventRecord = {
  id: string;
  file_id: string;
  message: string;
  level: string;
  service?: string;
  trace_id?: string;
  line_no?: number;
  timestamp?: string;
  created_at?: string;
};

export type SimilarEventMatch = {
  vector_id: string;
  distance?: number;
  event: EventRecord;
};

export type EventContext = {
  event: EventRecord;
  same_trace_id: EventRecord[];
  time_window: EventRecord[];
  line_window: EventRecord[];
  chunk_fallback?: {
    sequence_number?: number;
    content?: string;
  };
};

export type IncidentRecord = {
  id: string;
  title?: string;
  cluster_key?: string;
  severity?: string;
  status?: 'open' | 'resolved' | string;
  event_count?: number;
  event_ids?: string[];
  created_at?: string;
  updated_at?: string;
};

export type IncidentDetail = {
  incident: IncidentRecord;
  events: EventRecord[];
};
