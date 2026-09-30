import { useEffect, useRef } from "react";

/** Runs `loader` now and every `intervalMs`, pausing while the tab is hidden. */
export default function usePolling(loader, intervalMs) {
  const saved = useRef(loader);
  saved.current = loader;

  useEffect(() => {
    let timer = null;
    const tick = () => saved.current();
    const start = () => {
      if (timer === null) timer = setInterval(tick, intervalMs);
    };
    const stop = () => {
      clearInterval(timer);
      timer = null;
    };
    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        tick();
        start();
      }
    };

    tick();
    if (!document.hidden) start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [loader, intervalMs]);
}
