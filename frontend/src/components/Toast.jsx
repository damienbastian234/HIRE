import { AnimatePresence, motion } from "framer-motion";
import { FiCheckCircle, FiAlertTriangle, FiInfo, FiX } from "react-icons/fi";

const ICONS = {
  success: <FiCheckCircle className="text-success" size={18} />,
  error: <FiAlertTriangle className="text-alert" size={18} />,
  info: <FiInfo className="text-signal-dark" size={18} />,
};

/**
 * ToastContainer
 * Renders the active toast queue. Pair with the useToast hook:
 *
 *   const { toasts, addToast, removeToast } = useToast();
 *   addToast("Application submitted", "success");
 *   <ToastContainer toasts={toasts} onDismiss={removeToast} />
 *
 * Props:
 * - toasts: { id, message, variant }[]
 * - onDismiss: (id) => void
 */
export default function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-full max-w-sm flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.18 }}
            role="status"
            className="pointer-events-auto flex items-start gap-2.5 rounded-xl border border-ink/8 bg-white px-4 py-3 shadow-pop"
          >
            {ICONS[toast.variant] || ICONS.info}
            <p className="flex-1 text-sm text-ink">{toast.message}</p>
            <button
              onClick={() => onDismiss(toast.id)}
              aria-label="Dismiss notification"
              className="text-slate hover:text-ink"
            >
              <FiX size={15} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
