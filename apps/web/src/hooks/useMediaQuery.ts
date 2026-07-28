import { useEffect, useState } from 'react';

/**
 * Hook reativo para media queries do CSS.
 * Retorna `true` quando a query casa, `false` caso contrário.
 * Atualiza automaticamente quando a viewport muda.
 *
 * @example
 *   const isMobile = useMediaQuery('(max-width: 760px)');
 *   if (isMobile) return <MobileLayout />;
 */
export function useMediaQuery(query: string): boolean {
  const getInitial = (): boolean => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    return window.matchMedia(query).matches;
  };

  const [matches, setMatches] = useState<boolean>(getInitial);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    const mql = window.matchMedia(query);
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches);
    // Sincroniza estado inicial caso tenha mudado entre render e effect.
    setMatches(mql.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

/**
 * Breakpoints oficiais do Portal Vesper.
 * Mantidos sincronizados com media queries em `styles/index.css`.
 */
export const BREAKPOINTS = {
  /** até 760px: celular retrato e pequenos tablets em pé */
  mobile: '(max-width: 760px)',
  /** até 1100px: tablet em paisagem e notebooks pequenos */
  tablet: '(max-width: 1100px)',
  /** até 1200px: telas intermediárias */
  desktopCompact: '(max-width: 1200px)',
} as const;
