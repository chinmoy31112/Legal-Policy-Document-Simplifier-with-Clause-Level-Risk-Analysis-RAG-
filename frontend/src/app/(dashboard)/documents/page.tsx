"use client";

import Link from 'next/link';
import { useDocuments, useDeleteDocument } from '@/hooks/use-documents';
import { StatusBadge } from '@/components/documents/status-badge';
import { format } from 'date-fns';
import { FileText, MoreVertical, Trash2, ArrowRight, Upload } from 'lucide-react';
import { DocumentStatus } from '@/types/document';

export default function DocumentsPage() {
  const { data, isLoading, isError } = useDocuments(1, 20);
  const deleteMutation = useDeleteDocument();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center text-destructive">
        <p>Failed to load documents. Please try again later.</p>
      </div>
    );
  }

  const documents = data?.items || [];

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Documents</h1>
          <p className="text-muted-foreground mt-1">
            Manage and view your analyzed legal documents.
          </p>
        </div>
        <Link 
          href="/upload" 
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
        >
          <Upload className="w-4 h-4 mr-2" />
          Upload New
        </Link>
      </div>

      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 border rounded-xl bg-card text-center shadow-sm">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No documents yet</h3>
          <p className="text-muted-foreground max-w-sm mb-6">
            Upload your first legal document to get started with our AI risk analysis.
          </p>
          <Link 
            href="/upload" 
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
          >
            Upload Document
          </Link>
        </div>
      ) : (
        <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
              <tr>
                <th className="px-6 py-4 font-medium">Document Name</th>
                <th className="px-6 py-4 font-medium">Type</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Date Uploaded</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-muted/50 transition-colors">
                  <td className="px-6 py-4 font-medium flex items-center">
                    <FileText className="w-4 h-4 mr-3 text-primary" />
                    {doc.original_filename}
                  </td>
                  <td className="px-6 py-4 capitalize">
                    {doc.document_type.replace('_', ' ')}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">
                    {format(new Date(doc.created_at), 'MMM d, yyyy')}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button 
                        onClick={() => {
                          if (confirm('Are you sure you want to delete this document?')) {
                            deleteMutation.mutate(doc.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="p-2 text-muted-foreground hover:text-destructive transition-colors rounded-md hover:bg-destructive/10"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      
                      <Link 
                        href={`/analysis/${doc.id}`}
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring bg-secondary text-secondary-foreground hover:bg-secondary/80 h-8 px-3"
                      >
                        {doc.status === DocumentStatus.COMPLETED ? 'View Analysis' : 'View Status'}
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Link>
                    </div>
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
