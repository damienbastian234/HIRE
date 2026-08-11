import { useCallback, useRef, useState } from "react";
import { FiUploadCloud, FiFileText, FiX } from "react-icons/fi";
import Button from "./Button";

/**
 * ResumeUploadCard
 * Props:
 * - onFileSelect: (file: File) => void — called when a valid file is chosen
 * - accept: string — default ".pdf,.doc,.docx"
 * - maxSizeMb: number — default 5
 *
 * Usage:
 * <ResumeUploadCard onFileSelect={(file) => uploadResume(file)} />
 */
export default function ResumeUploadCard({ onFileSelect, accept = ".pdf,.doc,.docx", maxSizeMb = 5 }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");

  const handleFile = useCallback(
    (candidate) => {
      if (!candidate) return;
      const sizeOk = candidate.size / (1024 * 1024) <= maxSizeMb;
      if (!sizeOk) {
        setError(`File is larger than ${maxSizeMb}MB. Choose a smaller file.`);
        return;
      }
      setError("");
      setFile(candidate);
      onFileSelect?.(candidate);
    },
    [maxSizeMb, onFileSelect]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFile(e.dataTransfer.files?.[0]);
      }}
      className={`rounded-card border-2 border-dashed p-8 text-center transition-colors
        ${isDragging ? "border-signal-dark bg-signal/10" : "border-ink/15 bg-white"}`}
    >
      {!file ? (
        <>
          <FiUploadCloud className="mx-auto text-slate-light" size={30} />
          <p className="mt-3 text-sm font-medium text-ink">Drag and drop your resume here</p>
          <p className="mt-1 text-xs text-slate">PDF or Word, up to {maxSizeMb}MB</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => inputRef.current?.click()}
            type="button"
          >
            Choose file
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            onChange={(e) => handleFile(e.target.files?.[0])}
            className="hidden"
            aria-label="Upload resume"
          />
        </>
      ) : (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-paper px-4 py-3 text-left">
          <div className="flex min-w-0 items-center gap-2.5">
            <FiFileText className="shrink-0 text-signal-dark" size={18} />
            <span className="truncate text-sm text-ink">{file.name}</span>
          </div>
          <button
            onClick={() => {
              setFile(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            aria-label="Remove file"
            className="text-slate hover:text-alert"
          >
            <FiX size={16} />
          </button>
        </div>
      )}
      {error && <p className="mt-3 text-xs text-alert">{error}</p>}
    </div>
  );
}
