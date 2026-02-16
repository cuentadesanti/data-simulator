import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Tracks getBoundingClientRect() of a CSS selector.
 * Re-measures on scroll (capture phase on window + scrollable ancestors),
 * resize, and ResizeObserver on target. Retries via MutationObserver for
 * up to 2s if the target is not yet in the DOM.
 */
export function useTourPositioning(selector: string | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const elementRef = useRef<Element | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const mutationObserverRef = useRef<MutationObserver | null>(null);
  const scrollCleanupRef = useRef<(() => void) | null>(null);

  const measure = useCallback(() => {
    if (elementRef.current) {
      const r = elementRef.current.getBoundingClientRect();
      setRect((prev) => {
        if (
          prev &&
          prev.top === r.top &&
          prev.left === r.left &&
          prev.width === r.width &&
          prev.height === r.height
        ) {
          return prev;
        }
        return r;
      });
    }
  }, []);

  const attachScrollListeners = useCallback(
    (el: Element) => {
      const scrollHandlers: { target: Element | Window; handler: () => void }[] = [];

      // Walk up to find scrollable ancestors
      let parent = el.parentElement;
      while (parent) {
        const style = getComputedStyle(parent);
        const overflow = style.overflow + style.overflowX + style.overflowY;
        if (/auto|scroll/.test(overflow)) {
          const handler = () => measure();
          parent.addEventListener('scroll', handler, { passive: true });
          scrollHandlers.push({ target: parent, handler });
        }
        parent = parent.parentElement;
      }

      // Window scroll
      const windowHandler = () => measure();
      window.addEventListener('scroll', windowHandler, { capture: true, passive: true });
      scrollHandlers.push({ target: window, handler: windowHandler });

      scrollCleanupRef.current = () => {
        scrollHandlers.forEach(({ target, handler }) => {
          target.removeEventListener('scroll', handler);
        });
      };
    },
    [measure],
  );

  useEffect(() => {
    if (!selector) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clearing derived state when selector is removed
      setRect(null);
      return;
    }

    const cleanup = () => {
      observerRef.current?.disconnect();
      mutationObserverRef.current?.disconnect();
      scrollCleanupRef.current?.();
      observerRef.current = null;
      mutationObserverRef.current = null;
      scrollCleanupRef.current = null;
    };

    const attach = (el: Element) => {
      elementRef.current = el;
      measure();

      // ResizeObserver
      observerRef.current = new ResizeObserver(() => measure());
      observerRef.current.observe(el);

      // Scroll listeners
      attachScrollListeners(el);
    };

    // Try to find element immediately
    const el = document.querySelector(selector);
    if (el) {
      attach(el);
    } else {
      // Retry via MutationObserver for up to 2s
      const timeout = setTimeout(() => {
        mutationObserverRef.current?.disconnect();
        elementRef.current = null;
        setRect(null);
      }, 2000);

      mutationObserverRef.current = new MutationObserver(() => {
        const found = document.querySelector(selector);
        if (found) {
          clearTimeout(timeout);
          mutationObserverRef.current?.disconnect();
          attach(found);
        }
      });
      mutationObserverRef.current.observe(document.body, {
        childList: true,
        subtree: true,
      });
    }

    // Window resize
    const onResize = () => measure();
    window.addEventListener('resize', onResize);

    return () => {
      cleanup();
      window.removeEventListener('resize', onResize);
      elementRef.current = null;
    };
  }, [selector, measure, attachScrollListeners]);

  return rect;
}
