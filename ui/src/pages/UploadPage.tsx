import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getFiles, ingestFile, uploadFile } from 'api/files';
import { bytesToReadable, formatDate } from 'utils/format';

export const UploadPage = () => {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [statusByFile, setStatusByFile] = useState<Record<string, string>>({});

  const filesQuery = useQuery({ queryKey: ['files'], queryFn: getFiles, refetchInterval: 10000 });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadFile(file, setProgress),
    onSuccess: (data) => {
      setStatusByFile((prev) => ({ ...prev, [data.file_id]: 'uploaded' }));
      queryClient.invalidateQueries({ queryKey: ['files'] });
    }
  });

  const ingestMutation = useMutation({
    mutationFn: (fileId: string) => ingestFile(fileId),
    onSuccess: (data) => {
      setStatusByFile((prev) => ({ ...prev, [data.file_id]: data.status }));
    }
  });

  return (
    <section className="space-y-4">
      <div className="card p-5">
        <h1 className="text-lg font-semibold">File Upload</h1>
        <label className="mt-3 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/70 p-8 text-center hover:border-indigo-400">
          <input type="file" accept=".log,.txt" className="hidden" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} />
          <span className="text-sm text-slate-300">Drag & drop file or click to choose</span>
          {selectedFile ? (
            <span className="mt-2 text-xs text-slate-500">
              {selectedFile.name} • {bytesToReadable(selectedFile.size)}
            </span>
          ) : null}
        </label>

        <div className="mt-4 flex items-center gap-2">
          <button className="button" disabled={!selectedFile || uploadMutation.isPending} onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}>
            {uploadMutation.isPending ? 'Uploading...' : 'Upload file'}
          </button>
          {progress > 0 ? <span className="text-xs text-slate-500">Progress: {progress}%</span> : null}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="text-sm font-semibold">Upload history</h2>
        <div className="mt-3 space-y-2">
          {(filesQuery.data ?? []).map((file) => (
            <div key={file.file_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900 p-3">
              <div>
                <p className="text-sm text-slate-200">{file.filename}</p>
                <p className="text-xs text-slate-500">{file.file_id} • {formatDate(file.created_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{statusByFile[file.file_id] ?? 'uploaded'}</span>
                <button className="rounded border border-slate-700 px-3 py-1 text-xs hover:border-indigo-400" onClick={() => ingestMutation.mutate(file.file_id)}>
                  Ingest
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
