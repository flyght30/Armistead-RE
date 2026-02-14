import React, { useRef, useState } from 'react';
import { FileText, Download, File, Upload, X } from 'lucide-react';
import { TransactionFile } from '../../types/transaction';
import EmptyState from '../../components/ui/EmptyState';
import { useToast } from '../../components/ui/ToastContext';
import Spinner from '../../components/ui/Spinner';
import apiClient from '../../lib/api';

interface DocumentsTabProps {
  files: TransactionFile[];
  transactionId: string;
  onRefresh: () => void;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function formatContentType(contentType: string): string {
  const map: Record<string, string> = {
    'application/pdf': 'PDF Document',
    'image/jpeg': 'JPEG Image',
    'image/png': 'PNG Image',
  };
  if (map[contentType]) return map[contentType];
  const parts = contentType.split('/');
  return parts[parts.length - 1]?.toUpperCase() || 'File';
}

export default function DocumentsTab({ files, transactionId, onRefresh }: DocumentsTabProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Reset the input so the same file can be re-selected if needed
    e.target.value = '';

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      await apiClient.post(`/transactions/${transactionId}/files`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      toast('success', `"${selectedFile.name}" uploaded successfully.`);
      onRefresh();
    } catch (err: any) {
      const message =
        err?.response?.data?.detail || err?.message || 'Failed to upload file.';
      toast('error', message);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = (file: TransactionFile) => {
    window.open(file.url, '_blank');
  };

  return (
    <div>
      {/* Header with upload button */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs text-gray-500">PDF, JPEG, PNG up to 25MB</p>
        </div>
        <div className="flex items-center gap-3">
          {uploading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Spinner size="sm" />
              <span>Uploading...</span>
            </div>
          )}
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Upload className="w-4 h-4" />
            Upload File
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* File table or empty state */}
      {files.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload contracts, disclosures, and other documents for this transaction."
          action={{ label: 'Upload File', onClick: handleUploadClick }}
        />
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <File className="w-5 h-5 text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatContentType(file.content_type)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDate(file.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDownload(file)}
                      className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
