import React from 'react';

interface FilterBarProps {
  children: React.ReactNode;
  activeFilters?: string[];
  onClear?: () => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({ children, activeFilters = [], onClear }) => (
  <section className="filter-bar">
    <div className="filter-bar-controls">{children}</div>
    {activeFilters.length > 0 && (
      <div className="filter-bar-chips">
        {activeFilters.map((filter) => <span key={filter}>{filter}</span>)}
        {onClear && <button type="button" onClick={onClear}>Limpar filtros</button>}
      </div>
    )}
  </section>
);

export default FilterBar;
