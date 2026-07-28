import React from 'react';

// WebP assets are regenerated from the current official transparent PNG package.
import { kodaImages } from '../../assets/koda/kodaManifest';

export type KodaVariant =
  | 'hello'
  | 'thinking'
  | 'guide'
  | 'chat'
  | 'alert'
  | 'success'
  | 'analyst'
  | 'security'
  | 'supervisor'
  | 'working'
  | 'help'
  | 'empty';

export interface KodaMascotProps {
  variant?: KodaVariant;
  mood?: KodaVariant; // Alias for backward compatibility
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'hero';
  className?: string;
  alt?: string;
  decorative?: boolean;
  withGlow?: boolean;
  moodText?: string;
}

const variantMap: Record<KodaVariant, string> = kodaImages;

const sizeMap = {
  xs: { width: '48px', height: '48px' },
  sm: { width: '92px', height: '92px' },
  md: { width: '132px', height: '132px' },
  lg: { width: '178px', height: '178px' },
  xl: { width: '220px', height: '220px' },
  hero: { width: '280px', height: '280px' },
};

export const KodaMascot: React.FC<KodaMascotProps> = ({
  variant,
  mood = 'hello',
  size = 'md',
  className = '',
  alt,
  decorative = true,
  withGlow = false,
  moodText,
}) => {
  // Determine variant based on variant prop, falling back to mood prop
  const activeVariant = variant || mood;
  const imageSrc = variantMap[activeVariant] || kodaImages.hello;

  const sizeStyle = sizeMap[size] || sizeMap.md;

  const defaultAlt = decorative ? '' : `Mascote Koda em modo ${activeVariant}`;
  const finalAlt = alt !== undefined ? alt : defaultAlt;

  // Glow styling
  const glowStyle = withGlow
    ? {
        filter: 'drop-shadow(0 0 15px rgba(109, 40, 217, 0.4)) drop-shadow(0 0 30px rgba(56, 189, 248, 0.2))',
      }
    : {
        filter: 'drop-shadow(0 10px 15px rgba(2, 6, 23, 0.3))',
      };

  return (
    <div
      className={`relative inline-flex flex-col items-center justify-center select-none pointer-events-auto ${className}`}
      style={{ ...sizeStyle }}
    >
      {/* Speech Bubble / Mood Text */}
      {moodText && (
        <div className="absolute -top-10 bg-slate-900/95 border border-slate-700/50 backdrop-blur-md text-white text-xs px-3 py-1.5 rounded-xl shadow-lg whitespace-nowrap z-10 pointer-events-auto transition-all duration-300">
          {moodText}
          {/* Arrow pointing down */}
          <div className="absolute bottom-[-5px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-slate-900 border-r border-b border-slate-700/50 rotate-45"></div>
        </div>
      )}

      {/* Main Mascot Image */}
      <img
        src={imageSrc}
        alt={finalAlt}
        aria-hidden={decorative}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          padding: '6px', // Safe padding to prevent drop-shadow clipping
          maxWidth: '100%',
          maxHeight: '100%',
          ...glowStyle,
        }}
        className="transition-transform duration-300 hover:scale-105 cursor-pointer"
      />
    </div>
  );
};

export default KodaMascot;
