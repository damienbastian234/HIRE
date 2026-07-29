import { useState } from "react";
import { FiCheckCircle } from "react-icons/fi";
import ResumeUploadCard from "../components/ResumeUploadCard";
import Button from "../components/Button";
import LoadingSpinner from "../components/LoadingSpinner";
import ToastContainer from "../components/Toast";
import useToast from "../hooks/useToast";

export default function ResumeUploadPage() {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  const handleUpload = async () => {
    if (!file) {
      addToast("Choose a resume file first.", "error");
      return;
    }
    setIsUploading(true);
    // Replace with services/api.js -> uploadResume(file, onUploadProgress)
    await new Promise((resolve) => setTimeout(resolve, 1200));
    setIsUploading(false);
    setIsDone(true);
    addToast("Resume uploaded and parsed.", "success");
  };

  return (
    <div className="mx-auto max-w-xl">
      <span className="eyebrow">Resume</span>
      <h1 className="mt-2 text-2xl font-semibold">Upload your resume</h1>
      <p className="mt-1.5 text-sm text-slate">
        We parse your resume once and use it to compute a match score against every open role.
      </p>

      <div className="mt-8">
        {isDone ? (
          <div className="flex flex-col items-center justify-center rounded-card border border-success/30 bg-success/5 px-6 py-14 text-center">
            <FiCheckCircle className="text-success" size={30} />
            <h3 className="mt-3 font-display text-base font-semibold text-ink">Resume processed</h3>
            <p className="mt-1.5 max-w-sm text-sm text-slate">
              We picked up your skills and experience. Head to job listings to see your match scores.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-5"
              onClick={() => {
                setIsDone(false);
                setFile(null);
              }}
            >
              Upload another
            </Button>
          </div>
        ) : (
          <>
            <ResumeUploadCard onFileSelect={setFile} />
            <Button
              variant="signal"
              size="lg"
              className="mt-5 w-full"
              onClick={handleUpload}
              isLoading={isUploading}
            >
              {isUploading ? "Uploading" : "Upload resume"}
            </Button>
            {isUploading && (
              <div className="mt-4 flex justify-center">
                <LoadingSpinner size="sm" label="Parsing resume" />
              </div>
            )}
          </>
        )}
      </div>

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
