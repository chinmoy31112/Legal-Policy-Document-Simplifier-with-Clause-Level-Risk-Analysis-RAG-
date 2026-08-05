"use client";

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useRouter } from 'next/navigation';
import { UploadCloud, File as FileIcon, X, Loader2, AlertCircle } from 'lucide-react';
import { useUploadDocument } from '@/hooks/use-documents';
import type { DocumentType } from '@/types/document';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>('other');
  const [jurisdiction, setJurisdiction] = useState<string>('US');
  
  const uploadMutation = useUploadDocument();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleUpload = () => {
    if (!file) return;
    
    uploadMutation.mutate(
      { file, documentType: docType, jurisdiction },
      {
        onSuccess: (data) => {
          // Navigate to the analysis page for this document
          router.push(`/analysis/${data.id}`);
        },
      }
    );
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Upload Document</h1>
        <p className="text-muted-foreground mt-2">
          Upload a legal document to analyze its clauses and identify potential risks.
        </p>
      </div>

      <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 border-b bg-muted/30">
          <h2 className="font-semibold text-lg">Document Details</h2>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Document Type</label>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                <option value="terms_and_conditions">Terms of Service</option>
                <option value="privacy_policy">Privacy Policy</option>
                <option value="employment_contract">Employment Contract</option>
                <option value="rental_agreement">Rental Agreement</option>
                <option value="loan_agreement">Loan Agreement</option>
                <option value="eula">EULA</option>
                <option value="other">Other / General Contract</option>
              </select>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Jurisdiction (Optional)</label>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={jurisdiction}
                onChange={(e) => setJurisdiction(e.target.value)}
              >
                <option value="US">United States (General)</option>
                <option value="US-CA">California, US</option>
                <option value="US-NY">New York, US</option>
                <option value="UK">United Kingdom</option>
                <option value="EU">European Union</option>
                <option value="IN">India</option>
                <option value="AU">Australia</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">File</label>
            
            {!file ? (
              <div 
                {...getRootProps()} 
                className={`
                  border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
                  ${isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/50'}
                  ${isDragReject ? 'border-destructive bg-destructive/5' : ''}
                `}
              >
                <input {...getInputProps()} />
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-4">
                  <UploadCloud className="h-6 w-6 text-primary" />
                </div>
                <p className="text-sm font-medium">
                  {isDragActive ? "Drop the file here..." : "Drag & drop a file here, or click to select"}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Supports PDF, DOCX, and TXT (Max 50MB)
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/30">
                <div className="flex items-center space-x-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <FileIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button 
                  type="button"
                  onClick={(e) => { e.preventDefault(); setFile(null); }}
                  className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
                  disabled={uploadMutation.isPending}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>

          {uploadMutation.isError && (
            <div className="p-4 bg-destructive/10 text-destructive text-sm rounded-lg flex items-start">
              <AlertCircle className="h-5 w-5 mr-2 shrink-0 mt-0.5" />
              <span>
                {uploadMutation.error instanceof Error 
                  ? uploadMutation.error.message 
                  : 'An error occurred during upload. Please try again.'}
              </span>
            </div>
          )}
        </div>
        
        <div className="p-6 border-t bg-muted/20 flex justify-end">
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); handleUpload(); }}
            disabled={!file || uploadMutation.isPending}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-8"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              "Upload and Analyze"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
