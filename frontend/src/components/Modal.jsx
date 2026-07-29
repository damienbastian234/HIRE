import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { FiX } from "react-icons/fi";

/**
 * Modal
 * Props:
 * - isOpen: boolean
 * - onClose: () => void
 * - title: string
 * - children: ReactNode
 *
 * Usage:
 * <Modal isOpen={open} onClose={() => setOpen(false)} title="Confirm">
 *   <p>Are you sure?</p>
 * </Modal>
 */
export default function Modal({ isOpen, onClose, title, children }) {
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <motion.div
            className="absolute inset-0 bg-ink/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="relative z-10 w-full max-w-md rounded-card bg-white p-6 shadow-pop"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 id="modal-title" className="text-lg font-semibold">
                {title}
              </h2>
              <button
                onClick={onClose}
                aria-label="Close dialog"
                className="rounded-full p-1.5 text-slate hover:bg-ink/5 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-dark/60"
              >
                <FiX size={18} />
              </button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
