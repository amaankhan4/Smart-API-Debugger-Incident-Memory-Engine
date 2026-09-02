/** Mirrors the FastAPI response schemas in `app/schemas`. Keep in sync with the backend. */

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type LogLevel = 'TRACE' | 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';

export type ErrorCategory =
  | 'database'
  | 'network'
  | 'authentication'
  | 'authorization'
  | 'validation'
  | 'timeout'
  | 'rate_limit'
  | 'dependency'
  | 'configuration'
  | 'unknown';

export type FileStatus =
  | 'uploaded'
  | 'processing'
  | 'embedding'
  | 'analyzing'
  | 'completed'
  | 'failed';

export type EmbeddingStatus = 'pending' | 'queued' | 'completed' | 'failed';

export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'ignored';

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low';

export type NoteType = 'investigation' | 'root_cause' | 'fix' | 'follow_up' | 'general';

export type SearchMode = 'semantic' | 'keyword' | 'hybrid';

export type User = {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  created_at?: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type FileRecord = {
  file_id: string;
  user_id: string;
  filename: string;
  size_bytes: number;
  status: FileStatus;
  total_events: number;
  total_errors: number;
  total_chunks: number;
  error_message?: string | null;
  uploaded_at?: string | null;
  ingest_started_at?: string | null;
  ingest_completed_at?: string | null;
};

export type UploadResponse = {
  file_id: string;
  filename: string;
  size_bytes: number;
  status: FileStatus;
};

export type IngestResponse = {
  file_id: string;
  status: FileStatus;
  chunks_processed: number;
  events_created: number;
  lines_skipped: number;
  duration_ms: number;
};

export type EventRecord = {
  id: string;
  user_id: string;
  file_id: string;
  line_no: number;
  timestamp?: string | null;
  service: string;
  level: LogLevel;
  message: string;
  trace_id?: string | null;
  span_id?: string | null;
  correlation_id?: string | null;
  http_method?: string | null;
  path?: string | null;
  status_code?: number | null;
  exception?: string | null;
  language?: string | null;
  framework?: string | null;
  stack_trace?: string | null;
  error_category: ErrorCategory;
  embedding_id?: string | null;
  embedding_status: EmbeddingStatus;
  incident_id?: string | null;
  chunk_sequence?: number | null;
  created_at?: string | null;
};

export type EventContext = {
  event: EventRecord;
  strategy: 'trace_id' | 'time_window' | 'line_window' | 'raw_chunk' | 'unavailable';
  before: EventRecord[];
  after: EventRecord[];
  trace_events: EventRecord[];
  raw_chunk?: string | null;
  raw_chunk_sequence?: number | null;
};

export type SimilarEventMatch = {
  event: EventRecord;
  score: number;
  distance: number;
  matched_on: string[];
};

export type IncidentRecord = {
  id: string;
  user_id: string;
  title: string;
  summary: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  cluster_key: string;
  cluster_label?: number | null;
  event_count: number;
  error_category?: string | null;
  services: string[];
  endpoints: string[];
  file_ids: string[];
  representative_event_ids: string[];
  first_seen?: string | null;
  last_seen?: string | null;
  resolved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type IncidentTimelinePoint = {
  bucket: string;
  count: number;
};

export type IncidentDetail = {
  incident: IncidentRecord;
  representative_events: EventRecord[];
  timeline: IncidentTimelinePoint[];
  similar_incidents: { incident: IncidentRecord; score: number }[];
};

export type Note = {
  id: string;
  incident_id: string;
  user_id: string;
  author_name?: string | null;
  event_id?: string | null;
  note: string;
  type: NoteType;
  created_at?: string | null;
};

export type ClusterRunResponse = {
  clusters_created: number;
  clusters_updated: number;
  events_clustered: number;
  duration_ms: number;
  reason?: string | null;
};

export type SearchResult = {
  event: EventRecord;
  score: number;
  source: SearchMode;
  matched_on: string[];
};

export type SearchDegradedReason = 'vector_quota_exceeded' | 'vector_unavailable';

export type SearchResponse = {
  query: string;
  mode: SearchMode;
  took_ms: number;
  results: SearchResult[];
  total: number;
  degraded_reason?: SearchDegradedReason | null;
};

export type VectorQuota = {
  queries_used: number;
  queries_limit: number;
  updates_used: number;
  updates_limit: number;
  queries_exhausted: boolean;
  updates_exhausted: boolean;
  exhausted: boolean;
  resets_at: string;
};

export type CountPoint = { key: string; count: number };
export type TimePoint = { bucket: string; total: number; errors: number };

export type Analytics = {
  overview: {
    total_files: number;
    total_events: number;
    total_errors: number;
    error_rate: number;
    open_incidents: number;
    resolved_incidents: number;
    total_incidents: number;
    events_pending_embedding: number;
  };
  error_trend: TimePoint[];
  incidents_over_time: CountPoint[];
  errors_by_service: CountPoint[];
  errors_by_category: CountPoint[];
  top_recurring_errors: {
    signature: string;
    message: string;
    service: string;
    count: number;
    error_category: string;
    incident_id?: string | null;
  }[];
  most_affected_endpoints: CountPoint[];
  processing_status: { status: string; count: number }[];
};

