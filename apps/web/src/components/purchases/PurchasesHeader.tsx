import React from 'react';
import { RotateCcw, Plus } from 'lucide-react';
import { Button } from '../ui/Button';

interface PurchasesHeaderProps {
  onRefresh: () => void;
  onNewPurchase: () => void;
  loading: boolean;
}

export const PurchasesHeader: React.FC<PurchasesHeaderProps> = ({
  onRefresh,
  onNewPurchase,
  loading,
}) => {
  return (
    <div className="purchases-topbar">
      <div>
        <h1>Compras</h1>
        <p>Central inteligente para pesquisar, comparar, aprovar e acompanhar compras.</p>
      </div>
      <div className="purchases-topbar-actions">
        <Button
          variant="secondary"
          size="sm"
          leftIcon={<RotateCcw size={15} />}
          onClick={onRefresh}
          disabled={loading}
        >
          Atualizar dados
        </Button>
        <Button
          variant="primary"
          size="sm"
          leftIcon={<Plus size={15} />}
          onClick={onNewPurchase}
        >
          Nova compra
        </Button>
      </div>
    </div>
  );
};
