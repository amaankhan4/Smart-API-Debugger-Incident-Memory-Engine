import { api } from './client';
import type { FileRecord } from 'types/api';

export const uploadFile = async (
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ message: string; file_id: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (!evt.total || !onProgress) return;
      onProgress(Math.round((evt.loaded / evt.total) * 100));
    }
  });
  return data;
};

export const getFiles = async (): Promise<FileRecord[]> => {
  const { data } = await api.get('/upload/all-files');
  return data.data ?? [];
};

export const ingestFile = async (fileId: string) => {
  const { data } = await api.post(`/ingest/${fileId}`);
  return data;
};
