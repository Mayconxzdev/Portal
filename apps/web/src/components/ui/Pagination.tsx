import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({ page, totalPages, onPageChange }) => (
  <div className="pagination">
    <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)} leftIcon={<ChevronLeft size={14} />}>
      Anterior
    </Button>
    <span>Página {page} de {Math.max(totalPages, 1)}</span>
    <Button size="sm" variant="secondary" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)} rightIcon={<ChevronRight size={14} />}>
      Próxima
    </Button>
  </div>
);

export default Pagination;
