import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FiMapPin, FiClock, FiArrowLeft } from "react-icons/fi";
import Button from "../components/Button";
import Modal from "../components/Modal";
import MatchMeter from "../components/MatchMeter";
import ErrorState from "../components/ErrorState";
import ToastContainer from "../components/Toast";
import useToast from "../hooks/useToast";
import { applyJob, getJobById } from "../services/api";

export default function JobDetailsPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  useEffect(() => {
    getJobById(jobId).then(({ data }) => setJob(data.job || null));
  }, [jobId]);

  if (!job) {
    return (
      <div className="container-page py-16">
        <ErrorState
          title="Job not found"
          description="This listing may have been closed or the link is incorrect."
        />
      </div>
    );
  }

  const handleApply = async () => {
    setIsApplying(true);
    try {
      await applyJob(jobId, { message: "Interested in this role." });
      setIsModalOpen(false);
      addToast("Application submitted.", "success");
    } catch (error) {
      addToast(error.response?.data?.detail || "Unable to submit application.", "error");
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="container-page max-w-3xl py-10">
      <Link to="/jobs" className="flex items-center gap-1.5 text-sm text-slate hover:text-ink">
        <FiArrowLeft size={14} /> Back to jobs
      </Link>

      <div className="mt-6 flex items-start justify-between gap-4 rounded-card border border-ink/8 bg-white p-6">
        <div>
          <h1 className="text-2xl font-semibold">{job.title}</h1>
          <p className="mt-1 text-sm text-slate">{job.company}</p>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate">
            <span className="flex items-center gap-1.5">
              <FiMapPin size={13} /> {job.location}
            </span>
            <span className="flex items-center gap-1.5">
              <FiClock size={13} /> Posted {job.postedDaysAgo}d ago
            </span>
            <span className="rounded-full bg-ink/5 px-2 py-0.5 font-medium text-ink">{job.type}</span>
          </div>
        </div>
        <MatchMeter score={job.matchScore} />
      </div>

      <div className="mt-6 flex flex-wrap gap-1.5">
        {job.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-signal/12 px-2.5 py-1 text-xs font-medium text-signal-dark">
            {tag}
          </span>
        ))}
      </div>

      <section className="mt-8">
        <h2 className="font-display text-base font-semibold">About the role</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate">{job.description}</p>
      </section>

      <section className="mt-6">
        <h2 className="font-display text-base font-semibold">Responsibilities</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate">
          {job.responsibilities.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="mt-6">
        <h2 className="font-display text-base font-semibold">Requirements</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate">
          {job.requirements.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <div className="mt-8 flex items-center gap-3 border-t border-ink/8 pt-6">
        <span className="text-base font-medium text-ink">{job.salaryRange}</span>
        <Button variant="signal" size="lg" className="ml-auto" onClick={() => setIsModalOpen(true)}>
          Apply now
        </Button>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={`Apply to ${job.title}`}>
        <p className="text-sm text-slate">
          We'll send your uploaded resume and profile to {job.company}. You can withdraw anytime from your
          dashboard.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
            Cancel
          </Button>
          <Button variant="signal" onClick={handleApply} isLoading={isApplying}>
            Confirm application
          </Button>
        </div>
      </Modal>

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
