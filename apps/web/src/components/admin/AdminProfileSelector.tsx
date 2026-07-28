import React from 'react';
import { AccessProfilePreset } from './types';

interface AdminProfileSelectorProps {
  profiles: AccessProfilePreset[];
  selectedProfileId: string;
  onSelectProfile: (id: string) => void;
  selectedProfileWarnings: string[];
  permissionLabels: Record<string, string>;
}

export const AdminProfileSelector: React.FC<AdminProfileSelectorProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  selectedProfileWarnings,
}) => {
  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) || profiles[0];

  return (
    <>
      <section className="admin-profile-panel admin-profile-list-panel">
        <div className="admin-profile-panel-title">
          <h4>Perfis sugeridos</h4>
          <p>Escolha o perfil mais próximo da função real.</p>
        </div>
        <div className="admin-profile-scroll-list">
        {profiles.map((profile) => {
          const isActive = selectedProfileId === profile.id;
          return (
            <button
              key={profile.id}
              type="button"
              onClick={() => onSelectProfile(profile.id)}
              className={isActive ? 'is-active' : ''}
            >
              <span className="admin-profile-option-head">
                <strong>{profile.label}</strong>
                <em className={`risk-${profile.risk.toLowerCase()}`}>
                  Risco: {profile.risk}
                </em>
              </span>
              <span>{profile.description}</span>
            </button>
          );
        })}
        </div>
      </section>

      <section className="admin-profile-panel admin-profile-detail-panel">
        <div>
          <h3>{selectedProfile.label}</h3>
          <p>{selectedProfile.purpose}</p>
        </div>

        <div className="admin-human-list">
          <strong>Poderá</strong>
          <ul>
            {selectedProfile.positive.map((pos) => (
              <li key={pos}>{pos}</li>
            ))}
          </ul>
        </div>

        <div className="admin-human-list muted">
          <strong>Não poderá</strong>
          <ul>
            {selectedProfile.negative.map((neg) => (
              <li key={neg}>{neg}</li>
            ))}
          </ul>
        </div>

        <span className="admin-profile-chat-note">
          O Chat fica ativo globalmente para todos os usuários e não precisa de ajuste manual.
        </span>

        {selectedProfileWarnings.length > 0 && (
          <div className="admin-profile-warning-list">
            {selectedProfileWarnings.map((warning, index) => (
              <p key={index}>Atenção: {warning}</p>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
