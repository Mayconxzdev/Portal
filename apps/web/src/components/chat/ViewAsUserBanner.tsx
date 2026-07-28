import React from 'react';
import { EyeOff } from 'lucide-react';

interface ViewAsUserBannerProps {
  targetUsername: string;
  onStop: () => void;
}

export const ViewAsUserBanner: React.FC<ViewAsUserBannerProps> = ({ targetUsername, onStop }) => {
  return (
    <div style={styles.banner}>
      <div style={styles.content}>
        <EyeOff size={16} style={styles.icon} />
        <span>
          Modo visualização como usuário — <strong>{targetUsername}</strong> (Somente Leitura)
        </span>
      </div>
      <button onClick={onStop} style={styles.button}>
        Encerrar Simulação
      </button>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  banner: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#b45309', // amber-700
    color: '#ffffff',
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 500,
    gap: '12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    justifyContent: 'space-between',
    zIndex: 100,
  },
  content: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  icon: {
    color: '#fef3c7',
  },
  button: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    border: 'none',
    borderRadius: '4px',
    color: '#ffffff',
    padding: '4px 10px',
    fontSize: '11.5px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
};
