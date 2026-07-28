export type QueryValue = string | number | boolean | null | undefined;

const currentPath = () => `${window.location.pathname}${window.location.search}`;

export const getQueryParam = (key: string) => {
  return new URLSearchParams(window.location.search).get(key);
};

export const getQueryNumber = (key: string) => {
  const value = getQueryParam(key);
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const setQueryParams = (
  updates: Record<string, QueryValue>,
  options: { replace?: boolean } = { replace: true },
) => {
  const params = new URLSearchParams(window.location.search);
  Object.entries(updates).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '' || value === false) {
      params.delete(key);
    } else {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`;
  if (nextUrl === currentPath()) return;

  window.history[options.replace === false ? 'pushState' : 'replaceState'](null, '', nextUrl);
};

export const replaceQueryParams = (updates: Record<string, QueryValue>) => {
  setQueryParams(updates, { replace: true });
};
