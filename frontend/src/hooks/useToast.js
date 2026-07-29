import { useCallback, useState } from "react";

let idCounter = 0;

// Provides addToast/removeToast for any component; pair with <ToastContainer />.
export default function useToast() {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (message, variant = "info", duration = 3500) => {
      const id = ++idCounter;
      setToasts((current) => [...current, { id, message, variant }]);
      if (duration) {
        setTimeout(() => removeToast(id), duration);
      }
      return id;
    },
    [removeToast]
  );

  return { toasts, addToast, removeToast };
}
