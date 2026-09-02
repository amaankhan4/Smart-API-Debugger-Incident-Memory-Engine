import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { FileText, Loader2, Play, RotateCcw, Trash2, Upload, UploadCloud, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

import { errorMessage } from 'api/client';
import { deleteFile, getFiles, ingestFile, uploadFile } from 'api/files';
import { PageHeader } from 'components/PageHeader';
import { FileStatusBadge } from 'components/ui/Badges';
import { EmptyState, ErrorState, TableSkeleton } from 'components/ui/States';
import type { FileRecord } from 'types/api';
import { bytesToReadable, formatNumber, formatRelative } from 'utils/format';

type PendingUpload = { id: string; name: string; progress: number; error?: string };

const ACCEPTED = '.log,.txt,.json,.ndjson';
const POLL_INTERVAL_MS = 4000;

export const FilesPage = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);

  const [dragging, setDragging] = useState(false);
  const [pending, setPending] = useState<PendingUpload[]>([]);
  const [confirmDelete, setConfirmDelete] = useState<FileRecord | null>(null);

  const filesQuery = useQuery({
    queryKey: ['files'],
    queryFn: () => getFiles({ limit: 100 }),
    // Processing and embedding are asynchronous, so poll while any file is in flight.
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const inFlight = items.some((file) =>
        ['processing', 'embedding', 'analyzing'].includes(file.status)
      );
      return inFlight ? POLL_INTERVAL_MS : false;
    }
  });

  useEffect(() => {
    if (searchParams.get('upload') === '1') {
      inputRef.current?.click();
      searchParams.delete('upload');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const ingestMutation = useMutation({
    mutationFn: ({ fileId, force }: { fileId: string; force?: boolean }) =>
      ingestFile(fileId, force),
    onSuccess: (result) => {
      toast.success(
        `Ingested ${formatNumber(result.events_created)} events from ${result.chunks_processed} chunk(s)`
      );
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error) => toast.error(errorMessage(error, 'Ingestion failed'))
  });

  const deleteMutation = useMutation({
    mutationFn: (fileId: string) => deleteFile(fileId),
    onSuccess: () => {
      toast.success('File and its events were deleted');
      setConfirmDelete(null);
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error) => toast.error(errorMessage(error, 'Could not delete the file'))
  });

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length) return;

      for (const file of Array.from(fileList)) {
        const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        setPending((current) => [...current, { id, name: file.name, progress: 0 }]);

        try {
          await uploadFile(file, (percent) =>
            setPending((current) =>
              current.map((item) => (item.id === id ? { ...item, progress: percent } : item))
            )
          );
          setPending((current) => current.filter((item) => item.id !== id));
          toast.success(`${file.name} uploaded`);
          queryClient.invalidateQueries({ queryKey: ['files'] });
        } catch (error) {
          const message = errorMessage(error, 'Upload failed');
          setPending((current) =>
            current.map((item) => (item.id === id ? { ...item, error: message } : item))
          );
          toast.error(`${file.name}: ${message}`);
        }
      }
    },
    [queryClient]
  );

  const items = filesQuery.data?.items ?? [];

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        title="Files"
        description="Upload log files, then ingest them into structured events."
        actions={
          <button type="button" onClick={() => inputRef.current?.click()} className="btn-primary">
            <Upload size={14} />
            Select files
          </button>
        }
      />

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void handleFiles(event.dataTransfer.files);
        }}
        className={`panel flex flex-col items-center justify-center border-dashed px-6 py-10 text-center transition-colors ${
          dragging ? 'border-accent bg-accent-dim' : 'border-line'
        }`}
      >
        <UploadCloud size={22} className="mb-3 text-content-subtle" aria-hidden />
        <p className="text-sm font-medium">Drop log files here</p>
        <p className="mt-1 text-xs text-content-muted">
          Supports {ACCEPTED.replaceAll(',', ', ')} — multiple files at once
        </p>
        <button type="button" onClick={() => inputRef.current?.click()} className="btn-secondary mt-4">
          Browse files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="sr-only"
          onChange={(event) => {
            void handleFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>

      <AnimatePresence>
        {pending.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="panel mt-4 overflow-hidden"
          >
            <ul className="divide-y divide-line">
              {pending.map((item) => (
                <li key={item.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-mono text-xs">{item.name}</span>
                    <span className="shrink-0 text-2xs text-content-subtle">
                      {item.error ? 'Failed' : `${item.progress}%`}
                    </span>
                  </div>
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-hover">
                    <div
                      className={`h-full rounded-full transition-all ${
                        item.error ? 'bg-severity-critical' : 'bg-accent'
                      }`}
                      style={{ width: `${item.error ? 100 : item.progress}%` }}
                    />
                  </div>
                  {item.error && (
                    <p className="mt-1.5 text-2xs text-severity-critical">{item.error}</p>
                  )}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="panel mt-4">
        <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="text-sm font-semibold">Uploaded files</h2>
          <span className="text-xs text-content-subtle">{filesQuery.data?.total ?? 0} total</span>
        </header>

        {filesQuery.isLoading ? (
          <TableSkeleton rows={5} columns={6} />
        ) : filesQuery.isError ? (
          <ErrorState message={errorMessage(filesQuery.error)} onRetry={() => filesQuery.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FileText size={18} />}
            title="No files yet"
            description="Upload a log file to extract structured events, embeddings and incidents."
            action={
              <button type="button" onClick={() => inputRef.current?.click()} className="btn-primary">
                <Upload size={14} />
                Upload a log file
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-2xs uppercase tracking-wide text-content-subtle">
                <tr>
                  <th scope="col" className="px-5 py-2.5 font-medium">File</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Size</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Events</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Errors</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Uploaded</th>
                  <th scope="col" className="px-5 py-2.5 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((file) => {
                  const busy =
                    ingestMutation.isPending && ingestMutation.variables?.fileId === file.file_id;
                  const ingested = file.status === 'completed' || file.status === 'embedding';
                  return (
                    <tr key={file.file_id} className="transition-colors hover:bg-surface-hover">
                      <td className="max-w-[260px] px-5 py-3">
                        <div className="truncate font-mono text-xs" title={file.filename}>
                          {file.filename}
                        </div>
                        {file.error_message && (
                          <div className="mt-1 truncate text-2xs text-severity-critical" title={file.error_message}>
                            {file.error_message}
                          </div>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-xs text-content-muted">
                        {bytesToReadable(file.size_bytes)}
                      </td>
                      <td className="px-3 py-3 text-xs tabular-nums text-content-muted">
                        {formatNumber(file.total_events)}
                      </td>
                      <td className="px-3 py-3 text-xs tabular-nums">
                        <span className={file.total_errors > 0 ? 'text-severity-critical' : 'text-content-muted'}>
                          {formatNumber(file.total_errors)}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <FileStatusBadge status={file.status} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-xs text-content-muted">
                        {formatRelative(file.uploaded_at)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              ingestMutation.mutate({ fileId: file.file_id, force: ingested })
                            }
                            className="btn-secondary px-2 py-1 text-xs"
                            title={
                              file.status === 'failed'
                                ? 'Retry ingestion'
                                : ingested
                                  ? 'Re-ingest this file'
                                  : 'Ingest this file'
                            }
                          >
                            {busy ? (
                              <Loader2 size={13} className="animate-spin" aria-hidden />
                            ) : file.status === 'failed' || ingested ? (
                              <RotateCcw size={13} aria-hidden />
                            ) : (
                              <Play size={13} aria-hidden />
                            )}
                            {file.status === 'failed' ? 'Retry' : ingested ? 'Re-ingest' : 'Ingest'}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDelete(file)}
                            className="btn-ghost p-1.5"
                            title="Delete file"
                            aria-label={`Delete ${file.filename}`}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <AnimatePresence>
        {confirmDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/70"
              onClick={() => setConfirmDelete(null)}
              aria-hidden
            />
            <motion.div
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="delete-title"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              className="relative w-full max-w-sm rounded-xl border border-line bg-surface p-5 shadow-overlay"
            >
              <div className="flex items-start justify-between">
                <h3 id="delete-title" className="text-sm font-semibold">
                  Delete this file?
                </h3>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(null)}
                  className="btn-ghost -mr-1 -mt-1 p-1"
                  aria-label="Cancel"
                >
                  <X size={15} />
                </button>
              </div>
              <p className="mt-2 text-sm text-content-muted">
                <span className="font-mono text-xs text-content">{confirmDelete.filename}</span> and all{' '}
                {formatNumber(confirmDelete.total_events)} derived events will be permanently removed.
                This cannot be undone.
              </p>
              <div className="mt-5 flex justify-end gap-2">
                <button type="button" onClick={() => setConfirmDelete(null)} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(confirmDelete.file_id)}
                  className="btn-danger"
                >
                  {deleteMutation.isPending && <Loader2 size={13} className="animate-spin" aria-hidden />}
                  Delete
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
