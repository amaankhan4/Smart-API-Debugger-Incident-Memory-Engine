import { api } from './client';
import type { FileRecord, FileStatus, IngestResponse, Page, UploadResponse } from 'types/api';

export const uploadFile = async (
  file: File,
  onProgress?: (percent: number) => void,
  signal?: AbortSignal
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<UploadResponse>('/files', formData, {
    signal,
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      onProgress(Math.round((event.loaded / event.total) * 100));
    }
  });
  return data;
};

export const getFiles = async (params: { status?: FileStatus; limit?: number; offset?: number } = {}) => {
  const { data } = await api.get<Page<FileRecord>>('/files', { params });
  return data;
};

export const getFile = async (fileId: string) => {
  const { data } = await api.get<FileRecord>(`/files/${fileId}`);
  return data;
};

export const deleteFile = async (fileId: string) => {
  const { data } = await api.delete<{ message: string }>(`/files/${fileId}`);
  return data;
};

export const ingestFile = async (fileId: string, force = false) => {
  const { data } = await api.post<IngestResponse>(`/ingest/${fileId}`, null, { params: { force } });
  return data;
};

