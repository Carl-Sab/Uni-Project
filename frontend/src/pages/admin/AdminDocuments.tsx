import { useRef, useState } from "react";
import { RefreshCw, Trash2, Upload, FileText } from "lucide-react";
import {
  useAdminDocuments,
  useDeleteDocument,
  useReindexDocument,
  useUploadDocument,
} from "../../lib/adminQueries";
import { AdminButton, AdminCard, StatusPill } from "../../components/admin/ui";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function AdminDocuments() {
  const { data: documents, isLoading } = useAdminDocuments();
  const upload = useUploadDocument();
  const reindex = useReindexDocument();
  const remove = useDeleteDocument();

  const [dragging, setDragging] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("handbook");
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    setPendingFile(file);
  }

  async function confirmUpload() {
    if (!pendingFile) return;
    await upload.mutateAsync({ file: pendingFile, docType });
    setPendingFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">Documents</h1>
        <p className="mt-0.5 text-sm text-steel-500">
          Upload source PDFs and manage what the assistant retrieves from.
        </p>
      </div>

      <AdminCard className="p-5">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-6 py-8 text-center transition-colors duration-100 ${
            dragging ? "border-steel-500 bg-steel-50" : "border-steel-200 hover:border-steel-300"
          }`}
        >
          <Upload className="size-5 text-steel-400" />
          <p className="text-sm text-steel-600">
            Drag a PDF here, or <span className="font-medium text-steel-800">click to browse</span>
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {pendingFile && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-steel-200 bg-steel-50 px-4 py-3">
            <FileText className="size-4 text-steel-500" />
            <span className="text-sm text-steel-800">{pendingFile.name}</span>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="rounded-md border border-steel-200 bg-white px-2 py-1 text-sm text-steel-700"
            >
              <option value="handbook">Handbook</option>
              <option value="catalogue">Catalogue</option>
            </select>
            <div className="ml-auto flex gap-2">
              <AdminButton variant="secondary" onClick={() => setPendingFile(null)}>
                Cancel
              </AdminButton>
              <AdminButton onClick={confirmUpload} disabled={upload.isPending}>
                {upload.isPending ? "Uploading…" : "Upload & index"}
              </AdminButton>
            </div>
          </div>
        )}
      </AdminCard>

      <AdminCard className="overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-steel-100 bg-steel-50 text-xs font-medium text-steel-500">
            <tr>
              <th className="px-4 py-2.5">Filename</th>
              <th className="px-4 py-2.5">Type</th>
              <th className="px-4 py-2.5">Uploaded</th>
              <th className="px-4 py-2.5">Indexed</th>
              <th className="px-4 py-2.5">Chunks</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-steel-50">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-steel-400">
                  Loading…
                </td>
              </tr>
            ) : documents && documents.length > 0 ? (
              documents.map((d) => (
                <tr key={d.id} className="hover:bg-steel-50/60">
                  <td className="px-4 py-2.5 font-medium text-steel-800">{d.filename}</td>
                  <td className="px-4 py-2.5 text-steel-500">{d.doc_type}</td>
                  <td className="px-4 py-2.5 text-steel-500">{formatDate(d.uploaded_at)}</td>
                  <td className="px-4 py-2.5 text-steel-500">{formatDate(d.indexed_at)}</td>
                  <td className="px-4 py-2.5 tabular-nums text-steel-500">{d.chunk_count}</td>
                  <td className="px-4 py-2.5">
                    <StatusPill status={d.status} />
                    {(d.status === "pending" || d.status === "indexing") && (
                      <span className="ml-1.5 inline-block size-1.5 animate-pulse rounded-full bg-steel-400" />
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex justify-end gap-1">
                      <button
                        title="Re-index"
                        onClick={() => reindex.mutate(d.id)}
                        disabled={d.status === "indexing"}
                        className="flex size-7 items-center justify-center rounded-md text-steel-400 transition-colors duration-100 hover:bg-steel-100 hover:text-steel-700 disabled:opacity-40"
                      >
                        <RefreshCw className="size-3.5" />
                      </button>
                      {confirmDeleteId === d.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              remove.mutate(d.id);
                              setConfirmDeleteId(null);
                            }}
                            className="rounded-md bg-red-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-red-700"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="rounded-md px-2 py-1 text-[11px] font-medium text-steel-500 hover:bg-steel-100"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          title="Delete"
                          onClick={() => setConfirmDeleteId(d.id)}
                          className="flex size-7 items-center justify-center rounded-md text-steel-400 transition-colors duration-100 hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-steel-400">
                  No documents indexed yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </AdminCard>
    </div>
  );
}
