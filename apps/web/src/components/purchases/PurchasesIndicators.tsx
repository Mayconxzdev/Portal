import React from 'react';

export type PurchaseQueueFilter = 'all' | 'attention' | 'suppliers' | 'approval' | 'ready' | 'delivery';

interface IndicatorItem {
  key: PurchaseQueueFilter;
  label: string;
  value: number;
  icon: React.ReactNode;
}

interface PurchasesIndicatorsProps {
  indicatorItems: IndicatorItem[];
  purchaseFilter: PurchaseQueueFilter;
  onFilterChange: (key: PurchaseQueueFilter) => void;
}

export const PurchasesIndicators: React.FC<PurchasesIndicatorsProps> = ({
  indicatorItems,
  purchaseFilter,
  onFilterChange,
}) => {
  return (
    <div className="purchases-summary-strip" aria-label="Filtros da Central de Compras">
      {indicatorItems.map(item => (
        <button
          key={item.key}
          type="button"
          className={`purchase-indicator-card ${purchaseFilter === item.key ? 'active' : ''}`}
          onClick={() => onFilterChange(item.key)}
          aria-pressed={purchaseFilter === item.key}
        >
          <span>{item.icon}</span>
          <strong>{item.value}</strong>
          <small>{item.label}</small>
        </button>
      ))}
    </div>
  );
};
