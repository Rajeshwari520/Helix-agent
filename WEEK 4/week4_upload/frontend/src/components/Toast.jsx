import { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef();
  const show = useCallback((text, isError = false) => {
    setToast({ text, isError });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), isError ? 7000 : 3500);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div role="status" aria-live="polite">
        {toast && <div id="toast" className={`toast${toast.isError ? " err" : ""}`}>{toast.text}</div>}
      </div>
    </ToastContext.Provider>
  );
}
