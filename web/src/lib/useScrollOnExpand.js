import { createContext, useContext, useEffect } from "react";

/**
 * The modal's scrollable content element, shared with nested forms.
 *
 * Collapsible sections live in child components (ServiceModalForm, the
 * per-service container options form) but the scroll container belongs to the
 * modal, so the ref is passed down rather than re-derived.
 */
export const ScrollContainerContext = createContext(null);

/**
 * Scroll the modal's content to the bottom when a section expands.
 *
 * Expanding a collapsed section below the fold reveals nothing until the user
 * scrolls, which reads as the click having done nothing. The delay lets the
 * newly revealed content lay out first, so `scrollHeight` includes it.
 *
 * No-op when the section collapses, or when there is no scroll container
 * (rendered outside a modal, or in tests).
 *
 * @param {boolean} expanded whether the section is currently open
 */
export function useScrollOnExpand(expanded) {
  const containerRef = useContext(ScrollContainerContext);

  useEffect(() => {
    if (!expanded || !containerRef?.current) return;
    const timer = setTimeout(() => {
      containerRef.current?.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }, 50);
    return () => clearTimeout(timer);
  }, [expanded, containerRef]);
}
