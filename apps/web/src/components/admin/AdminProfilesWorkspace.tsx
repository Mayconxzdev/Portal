import React, { useMemo, useState, useEffect } from 'react';
import { Sparkles, Copy, Trash2, Plus, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Badge } from '../ui/Badge';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { AccessProfilePreset, ModuleItem, UserItem } from './types';

interface AdminProfilesWorkspaceProps {
  profiles: AccessProfilePreset[];
  modules: ModuleItem[];
  users: UserItem[];
  onSaveProfile: (profile: AccessProfilePreset) => void;
  onDeleteProfile: (profileId: string) => void;
  onUseDraftProfile: (profile: AccessProfilePreset) => void;
}

const normalizeId = (name: string) =>
  `profile-${name
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'perfil'}-${Math.random().toString(36).substring(2, 6)}`;

const generateSmartDraft = (
  name: string,
  risk: string,
  permissions: Record<number, string>,
  modules: ModuleItem[]
) => {
  const label = name.trim() || 'Novo perfil';
  const purpose = `Concede acesso operacional a quadros e informações de ${label}, mantendo aprovações e administração protegidas.`;
  
  const positive: string[] = ['Usar o Chat e Koda (padrão)'];
  const negative: string[] = [];
  
  modules.forEach(mod => {
    const level = permissions[mod.id] || 'NO_ACCESS';
    if (level === 'NO_ACCESS') {
      negative.push(`Acessar o módulo de ${mod.name}`);
    } else if (level === 'READ_ONLY') {
      positive.push(`Consultar informações em ${mod.name} (leitura)`);
      if (mod.code === 'admin') negative.push('Alterar configurações ou gerenciar usuários');
      if (mod.code === 'purchases') negative.push('Criar cotações ou aprovar compras');
    } else if (level === 'NORMAL') {
      positive.push(`Visualizar, criar e editar dados em ${mod.name}`);
      if (mod.code === 'admin') negative.push('Conceder acessos administrativos de alto risco');
      if (mod.code === 'purchases') negative.push('Aprovar compras com alçada superior');
    } else if (level === 'MANAGER') {
      positive.push(`Gerenciar recursos, aprovar e analisar dados em ${mod.name}`);
      if (mod.code === 'admin') negative.push('Realizar exclusões destrutivas sem conformidade');
    } else if (level === 'ADMIN') {
      positive.push(`Administrar plenamente todas as configurações de ${mod.name}`);
    }
  });

  const adminAccess = Object.entries(permissions).find(([modId, lvl]) => {
    const mod = modules.find(m => m.id === Number(modId));
    return mod?.code === 'admin' && ['ADMIN', 'MANAGER'].includes(lvl);
  });
  if (!adminAccess) {
    negative.push('Administrar usuários e perfis do Portal');
  }
  
  const purchasesAccess = Object.entries(permissions).find(([modId, lvl]) => {
    const mod = modules.find(m => m.id === Number(modId));
    return mod?.code === 'purchases' && ['ADMIN', 'MANAGER'].includes(lvl);
  });
  if (!purchasesAccess) {
    negative.push('Aprovar gastos e pedidos de compras corporativas');
  }

  const finalPositive = Array.from(new Set(positive)).slice(0, 5);
  const finalNegative = Array.from(new Set(negative)).slice(0, 5);

  return {
    purpose,
    positive: finalPositive,
    negative: finalNegative
  };
};

export const AdminProfilesWorkspace: React.FC<AdminProfilesWorkspaceProps> = ({
  profiles,
  modules,
  users,
  onSaveProfile,
  onDeleteProfile,
  onUseDraftProfile,
}) => {
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [mode, setMode] = useState<'create' | 'edit'>('create');
  
  // Form states
  const [formName, setFormName] = useState('');
  const [formRisk, setFormRisk] = useState<AccessProfilePreset['risk']>('Medio');
  const [formPermissions, setFormPermissions] = useState<Record<number, string>>({});
  const [formPurpose, setFormPurpose] = useState('');
  const [formPositiveText, setFormPositiveText] = useState('');
  const [formNegativeText, setFormNegativeText] = useState('');
  
  // Manual edit flags to prevent smart overwrite
  const [isPurposeEdited, setIsPurposeEdited] = useState(false);
  const [isPositiveEdited, setIsPositiveEdited] = useState(false);
  const [isNegativeEdited, setIsNegativeEdited] = useState(false);
  
  const [deletingProfile, setDeletingProfile] = useState<AccessProfilePreset | null>(null);

  // Initialize permissions
  useEffect(() => {
    if (mode === 'create' && !selectedProfileId) {
      const initialPerms: Record<number, string> = {};
      modules.forEach(m => {
        initialPerms[m.id] = m.code === 'chat' ? 'NORMAL' : (m.is_restricted ? 'NO_ACCESS' : 'READ_ONLY');
      });
      setFormPermissions(initialPerms);
    }
  }, [modules, mode, selectedProfileId]);

  // React to form input changes to generate smart suggestion
  useEffect(() => {
    const draft = generateSmartDraft(formName, formRisk, formPermissions, modules);
    
    if (!isPurposeEdited) {
      setFormPurpose(draft.purpose);
    }
    if (!isPositiveEdited) {
      setFormPositiveText(draft.positive.join('\n'));
    }
    if (!isNegativeEdited) {
      setFormNegativeText(draft.negative.join('\n'));
    }
  }, [formName, formRisk, formPermissions, modules, isPurposeEdited, isPositiveEdited, isNegativeEdited]);

  // Count active users with matching profile role names
  const activeUsersCount = useMemo(() => {
    if (mode !== 'edit' || !selectedProfileId) return 0;
    const profile = profiles.find(p => p.id === selectedProfileId);
    if (!profile) return 0;
    return users.filter(u => u.is_active && u.role_name && profile.roleNames?.includes(u.role_name)).length;
  }, [profiles, selectedProfileId, users, mode]);

  const handleSelectProfile = (profile: AccessProfilePreset) => {
    setSelectedProfileId(profile.id);
    setMode('edit');
    setFormName(profile.label);
    setFormRisk(profile.risk);
    
    const perms: Record<number, string> = {};
    modules.forEach(m => {
      perms[m.id] = profile.accessLevelByModule[m.code] || 'NO_ACCESS';
    });
    setFormPermissions(perms);
    setFormPurpose(profile.purpose || profile.description);
    setFormPositiveText((profile.positive || []).join('\n'));
    setFormNegativeText((profile.negative || []).join('\n'));
    
    // Mark as manual to avoid overriding the loaded profile data
    setIsPurposeEdited(true);
    setIsPositiveEdited(true);
    setIsNegativeEdited(true);
  };

  const handleCreateNewClick = () => {
    setSelectedProfileId(null);
    setMode('create');
    setFormName('');
    setFormRisk('Medio');
    
    const initialPerms: Record<number, string> = {};
    modules.forEach(m => {
      initialPerms[m.id] = m.code === 'chat' ? 'NORMAL' : (m.is_restricted ? 'NO_ACCESS' : 'READ_ONLY');
    });
    setFormPermissions(initialPerms);
    
    setIsPurposeEdited(false);
    setIsPositiveEdited(false);
    setIsNegativeEdited(false);
  };

  const handleCloneProfile = (profile: AccessProfilePreset, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedProfileId(null);
    setMode('create');
    setFormName(`${profile.label} (Cópia)`);
    setFormRisk(profile.risk);
    
    const perms: Record<number, string> = {};
    modules.forEach(m => {
      perms[m.id] = profile.accessLevelByModule[m.code] || 'NO_ACCESS';
    });
    setFormPermissions(perms);
    setFormPurpose(profile.purpose || profile.description);
    setFormPositiveText((profile.positive || []).join('\n'));
    setFormNegativeText((profile.negative || []).join('\n'));
    
    // Mark as manual to preserve clone text
    setIsPurposeEdited(true);
    setIsPositiveEdited(true);
    setIsNegativeEdited(true);
  };

  const handleCancelDeleteProfile = () => {
    setDeletingProfile(null);
  };

  const handleConfirmDeleteProfile = () => {
    if (!deletingProfile) return;
    onDeleteProfile(deletingProfile.id);
    if (selectedProfileId === deletingProfile.id) {
      handleCreateNewClick();
    }
    setDeletingProfile(null);
  };

  const handleDiscardChanges = () => {
    if (mode === 'edit' && selectedProfileId) {
      const original = profiles.find(p => p.id === selectedProfileId);
      if (original) {
        handleSelectProfile(original);
      }
    } else {
      handleCreateNewClick();
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    const id = mode === 'edit' && selectedProfileId ? selectedProfileId : normalizeId(formName);
    
    const accessLevelByModule: Record<string, string> = {};
    Object.entries(formPermissions).forEach(([modId, lvl]) => {
      const mod = modules.find(m => m.id === Number(modId));
      if (mod) {
        accessLevelByModule[mod.code] = lvl;
      }
    });

    const isIt = /ti|help|suporte/i.test(formName);
    const isAdmin = /admin|gerencia/i.test(formName);
    const roleNames = isAdmin ? ['ADMIN'] : isIt ? ['IT_TECH', 'USER'] : ['USER'];

    const savedProfile: AccessProfilePreset = {
      id,
      label: formName.trim(),
      roleNames,
      description: formPurpose.substring(0, 120),
      purpose: formPurpose,
      risk: formRisk,
      accessLevelByModule,
      positive: formPositiveText.split('\n').map(l => l.trim()).filter(Boolean),
      negative: formNegativeText.split('\n').map(l => l.trim()).filter(Boolean),
    };

    onSaveProfile(savedProfile);
    
    if (mode === 'create') {
      setSelectedProfileId(id);
      setMode('edit');
    }
  };

  return (
    <section className="admin-shell" style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: 24, padding: 0 }}>
      
      {/* LEFT PANEL: PROFILES LIST */}
      <div className="admin-profiles-catalog" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>Perfis de Acesso</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Selecione, edite ou crie presets para sugerir no cadastro.</p>
          </div>
          <Button type="button" variant="primary" size="sm" leftIcon={<Plus size={14} />} onClick={handleCreateNewClick}>
            Novo Perfil
          </Button>
        </div>

        <div className="admin-profile-scroll-list" style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 'calc(100vh - 250px)', overflowY: 'auto', paddingRight: 4 }}>
          {profiles.map((profile) => {
            const isSelected = selectedProfileId === profile.id && mode === 'edit';
            return (
              <article 
                className={`admin-profile-preview-card ${isSelected ? 'active' : ''}`} 
                key={profile.id}
                onClick={() => handleSelectProfile(profile)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  padding: '12px 16px',
                  background: 'var(--card-bg)',
                  border: isSelected ? '2px solid var(--primary-color)' : '1px solid var(--border-color)',
                  borderRadius: 12,
                  cursor: 'pointer',
                  position: 'relative',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: 14, color: 'var(--text-primary)' }}>{profile.label}</strong>
                  <span className={`admin-risk-badge risk-${profile.risk.toLowerCase()}`} style={{ fontSize: 11, fontWeight: 600 }}>
                    Risco {profile.risk}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, lineHeight: 1.4, textOverflow: 'ellipsis', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {profile.description || profile.purpose}
                </p>

                {/* Profile actions showing on hover / sutil */}
                <div 
                  className="profile-actions-overlay"
                  style={{
                    display: 'flex',
                    gap: 6,
                    alignSelf: 'flex-end',
                    marginTop: 2
                  }}
                >
                  <button 
                    type="button" 
                    title="Clonar Perfil" 
                    onClick={(e) => handleCloneProfile(profile, e)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: '4px',
                      cursor: 'pointer',
                      color: 'var(--text-muted)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '4px',
                      transition: 'background 0.2s, color 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-muted)';
                    }}
                  >
                    <Copy size={13} />
                  </button>
                  <button 
                    type="button" 
                    title="Excluir Perfil" 
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletingProfile(profile);
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: '4px',
                      cursor: 'pointer',
                      color: 'var(--color-danger, #ef4444)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '4px',
                      transition: 'background 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>

      {/* RIGHT PANEL: DYNAMIC CREATION & EDITION */}
      <form onSubmit={handleSave} className="admin-profile-draft-panel" style={{ display: 'flex', flexDirection: 'column', gap: 20, background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 16, padding: 20 }}>
        
        {/* Panel Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', borderBottom: '1px solid var(--border-color)', paddingBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {mode === 'create' ? 'Criar Novo Perfil' : `Editar Perfil: ${formName}`}
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Defina os níveis de acesso e revise a finalidade sugerida em tempo real.
            </p>
          </div>
          {mode === 'edit' && (
            <Badge variant="neutral">
              {activeUsersCount} usuários ativos
            </Badge>
          )}
        </div>

        {/* Basic fields */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16 }}>
          <Input 
            label="Nome do perfil" 
            value={formName} 
            onChange={(e) => setFormName(e.target.value)} 
            placeholder="Ex: Desenho 3D"
            required
          />
          <Select
            label="Risco sugerido"
            value={formRisk}
            onChange={(e) => setFormRisk(e.target.value as AccessProfilePreset['risk'])}
            options={[
              { value: 'Baixo', label: 'Baixo' },
              { value: 'Medio', label: 'Médio' },
              { value: 'Alto', label: 'Alto' },
              { value: 'Critico', label: 'Crítico' },
            ]}
          />
        </div>

        {/* Module Permissions Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Seleção de Permissões por Módulo</strong>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxHeight: 180, overflowY: 'auto', paddingRight: 4, background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 12 }}>
            {modules.filter(m => m.code !== 'chat').map((module) => {
              const currentLvl = formPermissions[module.id] || 'NO_ACCESS';
              return (
                <div key={module.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>{module.name}</span>
                  <div style={{ width: 120 }}>
                    <Select
                      value={currentLvl}
                      onChange={(e) => setFormPermissions({ ...formPermissions, [module.id]: e.target.value })}
                      style={{ marginBottom: 0, padding: '4px 8px', fontSize: 11 }}
                      options={[
                        { value: 'NO_ACCESS', label: 'Sem acesso' },
                        { value: 'READ_ONLY', label: 'Leitura' },
                        { value: 'NORMAL', label: 'Normal' },
                        { value: 'MANAGER', label: 'Gerente' },
                        { value: 'ADMIN', label: 'Admin' },
                      ]}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Smart Draft Area (Editable Grey Box) */}
        <article className="admin-profile-detail-panel admin-profile-panel" style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid var(--border-color)', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sparkles size={14} style={{ color: 'var(--primary-color)' }} />
              Sugestão de Rascunho Inteligente
            </span>
            {(isPurposeEdited || isPositiveEdited || isNegativeEdited) && (
              <button 
                type="button" 
                onClick={() => {
                  setIsPurposeEdited(false);
                  setIsPositiveEdited(false);
                  setIsNegativeEdited(false);
                }}
                style={{ background: 'transparent', border: 'none', color: 'var(--primary-color)', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
              >
                Regenerar Rascunho
              </button>
            )}
          </div>

          {/* Description */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>Finalidade / Descrição do Perfil</label>
            <textarea
              value={formPurpose}
              onChange={(e) => {
                setFormPurpose(e.target.value);
                setIsPurposeEdited(true);
              }}
              style={{ width: '100%', minHeight: 48, background: 'var(--input-bg)', border: '1px solid var(--border-color)', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: 'var(--text-primary)', fontFamily: 'inherit', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Poderá */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-success, #10b981)' }}>Poderá (Tópicos por linha)</label>
              <textarea
                value={formPositiveText}
                onChange={(e) => {
                  setFormPositiveText(e.target.value);
                  setIsPositiveEdited(true);
                }}
                placeholder="Ex: criar cotações"
                style={{ width: '100%', minHeight: 90, background: 'var(--input-bg)', border: '1px solid var(--border-color)', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: 'var(--text-primary)', fontFamily: 'inherit', resize: 'vertical' }}
              />
            </div>
            
            {/* Não Poderá */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-danger, #ef4444)' }}>Não poderá (Tópicos por linha)</label>
              <textarea
                value={formNegativeText}
                onChange={(e) => {
                  setFormNegativeText(e.target.value);
                  setIsNegativeEdited(true);
                }}
                placeholder="Ex: aprovar compras"
                style={{ width: '100%', minHeight: 90, background: 'var(--input-bg)', border: '1px solid var(--border-color)', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: 'var(--text-primary)', fontFamily: 'inherit', resize: 'vertical' }}
              />
            </div>
          </div>
        </article>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
          {mode === 'create' ? (
            <>
              <Button type="button" variant="secondary" onClick={handleDiscardChanges}>
                Cancelar
              </Button>
              <Button type="submit" variant="primary" disabled={!formName.trim()}>
                Salvar Novo Perfil
              </Button>
            </>
          ) : (
            <>
              <Button 
                type="button" 
                variant="ghost" 
                style={{ color: 'var(--color-danger)', border: '1px solid rgba(239, 68, 68, 0.2)' }}
                onClick={() => {
                  const p = profiles.find(profile => profile.id === selectedProfileId);
                  if (p) setDeletingProfile(p);
                }}
              >
                Excluir Perfil
              </Button>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button type="button" variant="secondary" onClick={handleDiscardChanges}>
                  Descartar
                </Button>
                <Button type="submit" variant="primary" disabled={!formName.trim()}>
                  Salvar Alterações
                </Button>
              </div>
            </>
          )}
        </div>
      </form>

      {/* Exclude Profile Modal Confirmation */}
      {deletingProfile && (
        <ConfirmDialog
          isOpen={Boolean(deletingProfile)}
          onClose={handleCancelDeleteProfile}
          onConfirm={handleConfirmDeleteProfile}
          title="Excluir Perfil"
          message={`Deseja mesmo excluir o perfil "${deletingProfile.label}"? Usuários vinculados a ele perderão o acesso padrão sugerido.`}
          confirmText="Sim, Excluir Perfil"
          variant="danger"
        />
      )}
    </section>
  );
};
