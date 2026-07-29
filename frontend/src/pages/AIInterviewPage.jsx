import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FiMic, FiCheckCircle } from "react-icons/fi";
import Button from "../components/Button";
import LoadingSpinner from "../components/LoadingSpinner";
import { mockInterviewQuestions } from "../services/mockData";

export default function AIInterviewPage() {
  const [started, setStarted] = useState(false);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [finished, setFinished] = useState(false);

  const current = mockInterviewQuestions[index];
  const isLast = index === mockInterviewQuestions.length - 1;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    // Replace with services/api.js -> submitInterviewAnswer(sessionId, { questionId, answerText })
    await new Promise((resolve) => setTimeout(resolve, 700));
    setIsSubmitting(false);
    setAnswer("");
    if (isLast) {
      setFinished(true);
    } else {
      setIndex((i) => i + 1);
    }
  };

  if (!started) {
    return (
      <div className="container-page flex min-h-[60vh] flex-col items-center justify-center py-16 text-center">
        <span className="eyebrow">AI interview</span>
        <h1 className="mt-3 max-w-lg text-2xl font-semibold sm:text-3xl">
          Practice three questions, get honest feedback
        </h1>
        <p className="mt-3 max-w-md text-sm text-slate">
          Answers are typed for this demo. In production this screen also supports recorded audio.
        </p>
        <Button
          variant="signal"
          size="lg"
          className="mt-8"
          onClick={() => {
            // Replace with services/api.js -> startInterview(jobId)
            setStarted(true);
          }}
        >
          Start interview
        </Button>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="container-page flex min-h-[60vh] flex-col items-center justify-center py-16 text-center">
        <FiCheckCircle className="text-success" size={34} />
        <h1 className="mt-4 text-2xl font-semibold">Interview complete</h1>
        <p className="mt-2 max-w-md text-sm text-slate">
          Your responses are being scored. Results will appear on your dashboard shortly.
        </p>
      </div>
    );
  }

  return (
    <div className="container-page max-w-2xl py-14">
      <div className="flex items-center justify-between">
        <span className="eyebrow">
          Question {index + 1} of {mockInterviewQuestions.length}
        </span>
        <div className="flex items-center gap-1.5">
          {mockInterviewQuestions.map((q, i) => (
            <span
              key={q.id}
              className={`h-1.5 w-8 rounded-full ${i <= index ? "bg-signal-dark" : "bg-ink/10"}`}
            />
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={current.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.25 }}
          className="mt-6 rounded-card border border-ink/8 bg-white p-6"
        >
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-signal">
              <FiMic size={16} />
            </span>
            <p className="pt-1.5 font-display text-base font-medium text-ink">{current.prompt}</p>
          </div>

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={6}
            placeholder="Type your answer..."
            className="mt-5 w-full resize-none rounded-xl border border-ink/12 bg-paper px-4 py-3 text-sm text-ink placeholder:text-slate-light focus:border-signal-dark/60 focus:outline-none focus:ring-2 focus:ring-signal-dark/60"
          />

          <div className="mt-4 flex justify-end">
            <Button
              variant="signal"
              onClick={handleSubmit}
              disabled={!answer.trim()}
              isLoading={isSubmitting}
            >
              {isLast ? "Finish interview" : "Next question"}
            </Button>
          </div>
        </motion.div>
      </AnimatePresence>

      {isSubmitting && (
        <div className="mt-4 flex justify-center">
          <LoadingSpinner size="sm" label="Submitting answer" />
        </div>
      )}
    </div>
  );
}
