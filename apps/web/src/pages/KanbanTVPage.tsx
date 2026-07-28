import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Clock, LogOut, WifiOff, Settings, X, Play, Pause } from 'lucide-react';
import { apiJson } from '../components/kanban/kanbanApi';
import { KanbanCard, TVData } from '../components/kanban/types';

interface Props {
  boardId: number;
  onExit: () => void;
}

type TVLayout = 'COLUMNS' | 'URGENCY' | 'PRODUCTION' | 'COMPACT' | 'TV_LIST' | 'PRODUCTION_LIST';

const layoutLabels: Record<TVLayout, string> = {
  COLUMNS: 'Colunas',
  URGENCY: 'Urgência',
  PRODUCTION: 'Produção Cards',
  COMPACT: 'Compacto',
  TV_LIST: 'Lista',
  PRODUCTION_LIST: 'Produção Lista',
};

interface LocalSettings {
  theme: 'dark' | 'light' | 'factory';
  layout: TVLayout;
  showClock: boolean;
  showBoardName: boolean;
  showLayoutName: boolean;
  showKpis: boolean;
  showRanking: boolean;
  showExitButton: boolean;
  showDescription: boolean;
  showAssignees: boolean;
  showLabels: boolean;
  showChecklist: boolean;
  fontSize: 'small' | 'medium' | 'large' | 'xlarge';
  density: 'compact' | 'medium' | 'factory';
  autoScroll: boolean;
  autoScrollSeconds: number;
  visibleRows: number;
  hiddenColumns: number[];
  hiddenFields: string[];
}

export const KanbanTVPage: React.FC<Props> = ({ boardId, onExit }) => {
  const [data, setData] = useState<TVData | null>(null);
  const [connection, setConnection] = useState<'online' | 'reconnecting' | 'offline'>('reconnecting');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [now, setNow] = useState(new Date());
  
  const snapshotStorageKey = `vesper.kanban.tv.snapshot.${boardId}`;
  const settingsStorageKey = `vesper.kanban.tv.settings.${boardId}`;
  
  const params = new URLSearchParams(window.location.search);
  const tvMode = params.get('mode') === 'external' ? 'external' : 'meeting';

  // Opções locais de customização
  const [showConfig, setShowConfig] = useState(false);
  const [localSettings, setLocalSettings] = useState<Partial<LocalSettings>>(() => {
    const saved = localStorage.getItem(settingsStorageKey);
    if (saved) {
      try { return JSON.parse(saved); } catch {
        // Ignora falhas de parse de configuração
      }
    }
    return {};
  });

  const load = async () => {
    try {
      const payload = await apiJson<TVData>(`/api/v1/kanban/boards/${boardId}/tv-data?_=${Date.now()}`);
      setData(payload);
      setConnection('online');
      setLastUpdated(new Date());
      localStorage.setItem(snapshotStorageKey, JSON.stringify({ saved_at: new Date().toISOString(), payload }));
    } catch {
      const cached = localStorage.getItem(snapshotStorageKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        setData(parsed.payload);
        setLastUpdated(new Date(parsed.saved_at));
      }
      setConnection('offline');
    }
  };

  useEffect(() => {
    load();
    const clock = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(clock);
  }, [boardId]);

  useEffect(() => {
    if (!data) return;
    const poll = window.setInterval(load, Math.max(data.config.refresh_interval_seconds || 30, 10) * 1000);
    return () => window.clearInterval(poll);
  }, [data?.config.refresh_interval_seconds, boardId]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/kanban?board_id=${boardId}`);
    socket.onopen = () => setConnection('online');
    socket.onmessage = () => load();
    socket.onerror = () => setConnection('reconnecting');
    socket.onclose = () => setConnection((prev) => prev === 'offline' ? 'offline' : 'reconnecting');
    return () => socket.close();
  }, [boardId]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onExit();
      if (event.key.toLowerCase() === 'r') load();
      if (event.key.toLowerCase() === 'f') {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
        else document.exitFullscreen?.().catch(() => {});
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onExit]);

  // Mescla configurações (Padrão Backend + Customizações do Usuário)
  const settings = useMemo<LocalSettings>(() => {
    if (!data) {
      return {
        theme: (tvMode === 'external' ? 'factory' : 'dark') as any,
        layout: 'COLUMNS',
        showClock: true,
        showBoardName: true,
        showLayoutName: true,
        showKpis: true,
        showRanking: true,
        showExitButton: true,
        showDescription: true,
        showAssignees: true,
        showLabels: true,
        showChecklist: true,
        fontSize: 'medium',
        density: 'medium',
        autoScroll: true,
        autoScrollSeconds: 18,
        visibleRows: 16,
        hiddenColumns: [],
        hiddenFields: []
      };
    }

    const displayOptions = { ...(data.config.display_options || {}), ...(tvMode === 'external' ? (data.config.external_mode_options?.display_options || {}) : {}) };
    const kpiOptions = { ...(data.config.kpi_options || {}), ...(tvMode === 'external' ? (data.config.external_mode_options?.kpi_options || {}) : {}) };
    const layoutOptions = { ...(data.config.layout_options || {}), ...(tvMode === 'external' ? (data.config.external_mode_options?.layout_options || {}) : {}) };

    const defaults: LocalSettings = {
      theme: (tvMode === 'external' ? 'factory' : 'dark') as any,
      layout: (localSettings.layout || data.config.layout_type || 'COLUMNS') as TVLayout,
      showClock: displayOptions.show_clock !== false,
      showBoardName: displayOptions.show_board_name !== false,
      showLayoutName: displayOptions.show_layout_name !== false,
      showKpis: kpiOptions.show_kpis !== false,
      showRanking: layoutOptions.show_ranking !== false,
      showExitButton: displayOptions.show_exit_button !== false,
      showDescription: true,
      showAssignees: true,
      showLabels: true,
      showChecklist: true,
      fontSize: (layoutOptions.font_scale || 'medium') as any,
      density: (layoutOptions.density || 'medium') as any,
      autoScroll: layoutOptions.auto_scroll !== false,
      autoScrollSeconds: Number(layoutOptions.auto_scroll_seconds || 18),
      visibleRows: layoutOptions.visible_rows === 'auto' ? 16 : Number(layoutOptions.visible_rows || 16),
      hiddenColumns: [],
      hiddenFields: []
    };

    return { ...defaults, ...localSettings };
  }, [data, localSettings, tvMode]);

  const updateSetting = (key: keyof LocalSettings, value: any) => {
    const next = { ...localSettings, [key]: value };
    setLocalSettings(next);
    localStorage.setItem(settingsStorageKey, JSON.stringify(next));
  };

  const applyPreset = (preset: 'factory' | 'meeting' | 'operator') => {
    let next: Partial<LocalSettings> = {};
    if (preset === 'factory') {
      next = {
        theme: 'factory',
        layout: 'TV_LIST',
        showClock: false,
        showBoardName: false,
        showLayoutName: false,
        showKpis: false,
        showRanking: false,
        showExitButton: false,
        showDescription: false,
        showAssignees: false,
        showLabels: false,
        showChecklist: false,
        fontSize: 'xlarge',
        density: 'factory',
        autoScroll: true,
        autoScrollSeconds: 18,
        visibleRows: 16,
      };
    } else if (preset === 'meeting') {
      next = {
        theme: 'dark',
        layout: 'COLUMNS',
        showClock: true,
        showBoardName: true,
        showLayoutName: true,
        showKpis: true,
        showRanking: true,
        showExitButton: true,
        showDescription: true,
        showAssignees: true,
        showLabels: true,
        showChecklist: true,
        fontSize: 'medium',
        density: 'medium',
        autoScroll: true,
        autoScrollSeconds: 18,
      };
    } else if (preset === 'operator') {
      next = {
        theme: 'light',
        layout: 'PRODUCTION_LIST',
        showClock: true,
        showBoardName: true,
        showLayoutName: true,
        showKpis: true,
        showRanking: false,
        showExitButton: true,
        showDescription: true,
        showAssignees: true,
        showLabels: true,
        showChecklist: true,
        fontSize: 'medium',
        density: 'compact',
        autoScroll: false,
      };
    }
    setLocalSettings(next);
    localStorage.setItem(settingsStorageKey, JSON.stringify(next));
  };

  const critical = useMemo(() => [...(data?.critical_cards || [])].slice(0, 8), [data]);

  if (!data) {
    return (
      <div style={settings.theme === 'factory' ? undefined : tvRoot} className={settings.theme === 'factory' ? 'tv-factory-root' : undefined}>
        <div style={{ display: 'grid', placeItems: 'center', minHeight: '70vh', textAlign: 'center' }}>
          <div>
            <h1 className={settings.theme === 'factory' ? 'text-3xl font-black' : undefined} style={settings.theme === 'factory' ? undefined : { color: '#fff', fontSize: 36 }}>Modo TV/Foco</h1>
            <p className="text-slate-500 font-bold mt-2">Carregando painel operacional...</p>
            <button className="btn btn-secondary mt-4" onClick={load}>Tentar novamente</button>
          </div>
        </div>
      </div>
    );
  }

  // Filtra cards e colunas ocultas
  const filteredColumns = data.columns.filter(col => !settings.hiddenColumns.includes(col.id));
  const filteredCards = data.cards.filter(card => {
    // Esconde se a coluna estiver oculta
    if (settings.hiddenColumns.includes(card.column_id)) return false;
    return true;
  });

  const secondsAgo = lastUpdated ? Math.max(Math.floor((now.getTime() - lastUpdated.getTime()) / 1000), 0) : 0;
  const isFactory = settings.theme === 'factory';
  const isLight = settings.theme === 'light';

  // Custom fields
  const activeCustomFieldKeys = new Set((data.board.custom_fields || []).map((field: any) => field.key));
  const configuredTvFields = (
    (tvMode === 'external' ? data.config.external_mode_options?.visible_custom_fields : data.config.visible_custom_fields) 
    || data.config.visible_custom_fields 
    || ['title', ...(data.production_fields || []), 'due_date']
  ).filter((field: string) => {
    if (settings.hiddenFields.includes(field)) return false;
    return field === 'title' || field === 'due_date' || activeCustomFieldKeys.has(field);
  });

  // Tema Styles
  const themeClass = isFactory ? 'tv-factory-root' : isLight ? 'bg-slate-50 text-slate-800 min-h-screen p-4 flex flex-col font-sans' : 'min-h-screen p-4 flex flex-col font-sans bg-slate-950 text-slate-100';

  return (
    <div className={`kanban-tv-root ${themeClass} ${isFactory ? 'factory-theme' : ''}`} style={isFactory || isLight ? undefined : { background: '#020617', minHeight: '100vh', padding: '24px', display: 'flex', flexDirection: 'column' }}>
      {/* HEADER */}
      <header className={isFactory ? 'tv-factory-header' : undefined} style={isFactory ? undefined : {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingBottom: '16px',
        marginBottom: '20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        <div>
          {settings.showBoardName && (
            <h1 className={isFactory ? 'tv-factory-title' : 'text-slate-100 font-extrabold'} style={isFactory ? undefined : { fontSize: '28px', fontWeight: 900, color: '#f8fafc', margin: 0 }}>
              {data.board.name}
            </h1>
          )}
          {settings.showLayoutName && (
            <p style={{ color: '#64748b', fontSize: '12px', fontWeight: 600, marginTop: '4px', margin: 0 }}>
              Painel: <strong style={{ color: '#3b82f6' }}>{layoutLabels[settings.layout]}</strong> · atualizado há {secondsAgo}s
            </p>
          )}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {settings.showClock && (
            <strong className={isFactory ? 'tv-factory-clock' : undefined} style={isFactory ? undefined : { color: '#e2e8f0', fontSize: '20px', fontWeight: 700, fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} /> {now.toLocaleTimeString('pt-BR')}
            </strong>
          )}
          {settings.showExitButton && (
            <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: '#fff', borderRadius: '6px', cursor: 'pointer' }} onClick={onExit}>
              <LogOut size={14} /> Sair
            </button>
          )}
          {/* Botão de configuração discreto */}
          <button 
            style={{
              padding: '8px',
              borderRadius: '50%',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={() => setShowConfig(!showConfig)}
            title="Configurar Exibição da TV"
          >
            <Settings size={18} />
          </button>
        </div>
      </header>

      {connection === 'offline' && (
        <div className="offline-banner mb-4">
          <WifiOff size={20} />
          <div>
            <div className="offline-banner-title">Modo offline</div>
            <div className="offline-banner-text">Exibindo último snapshot as {lastUpdated?.toLocaleTimeString('pt-BR')}.</div>
          </div>
        </div>
      )}

      {settings.showKpis && (
        <section className={isFactory ? 'tv-factory-metric-row' : undefined} style={isFactory ? undefined : {
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: '16px',
          marginBottom: '20px'
        }}>
          <Metric label="Cards ativos" value={data.metrics.total_active_cards || 0} isFactory={isFactory} />
          <Metric label="Críticos" value={data.metrics.critical_cards || 0} danger={Number(data.metrics.critical_cards) > 0} isFactory={isFactory} />
          <Metric label="Atrasados" value={data.metrics.overdue_cards || 0} danger={Number(data.metrics.overdue_cards) > 0} isFactory={isFactory} />
          <Metric label="Vence hoje" value={data.metrics.due_today_cards || 0} isFactory={isFactory} />
          <Metric label="Sem responsável" value={data.metrics.unassigned_cards || 0} isFactory={isFactory} />
        </section>
      )}

      {/* CONTEÚDO PRINCIPAL */}
      <div style={{ display: 'grid', gridTemplateColumns: settings.showRanking && critical.length > 0 ? '1fr 300px' : '1fr', gap: '16px', flex: 1 }}>
        <main style={{ overflow: 'auto' }}>
          {settings.layout === 'TV_LIST' || settings.layout === 'PRODUCTION_LIST' ? (
            <TVList 
              cards={filteredCards} 
              fields={configuredTvFields} 
              production={settings.layout === 'PRODUCTION_LIST'} 
              settings={settings} 
              columns={data.columns} 
              customFields={data.board.custom_fields || []} 
            />
          ) : settings.layout === 'URGENCY' ? (
            <UrgencyLayout cards={filteredCards} isFactory={isFactory} />
          ) : (
            <ColumnsLayout columns={filteredColumns} cards={filteredCards} settings={settings} />
          )}
        </main>

        {settings.showRanking && critical.length > 0 && (
          <aside className={isFactory ? 'tv-factory-metric p-4 space-y-3' : 'bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-3'}>
            <h2 className="text-red-500 font-extrabold flex gap-2 items-center text-sm uppercase">
              <AlertTriangle size={16} /> Ranking Crítico
            </h2>
            {critical.slice(0, 8).map((card: any, index) => (
              <div key={card.id} className="p-2 bg-red-50 border border-red-200 rounded text-slate-800 font-bold text-xs">
                #{index + 1} {card.title}
                <div className="text-[10px] text-slate-500">{card.urgency_score} pts · {(card.urgency_reasons || []).join(' · ')}</div>
              </div>
            ))}
          </aside>
        )}
      </div>

      {/* DRAWER / MODAL DE CONFIGURAÇÃO FLUTUANTE */}
      {showConfig && (
        <div className="kanban-tv-config-panel fixed inset-y-0 right-0 w-80 shadow-2xl z-50 p-6 overflow-y-auto font-sans text-xs font-bold flex flex-col justify-between">
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b pb-3">
              <h2 className="text-sm font-black uppercase tracking-wider text-slate-950">Ajustes da TV Fábrica</h2>
              <button onClick={() => setShowConfig(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
            </div>

            {/* PRESETS RÁPIDOS */}
            <div className="space-y-2">
              <span className="block text-slate-500 text-[10px] uppercase font-black">Predefinições Rápidas</span>
              <div className="grid grid-cols-3 gap-2">
                <button onClick={() => applyPreset('factory')} className="p-2 border border-slate-300 rounded text-center bg-blue-50 hover:bg-blue-100 font-bold text-[10px]">TV Fábrica</button>
                <button onClick={() => applyPreset('meeting')} className="p-2 border border-slate-300 rounded text-center bg-purple-50 hover:bg-purple-100 font-bold text-[10px]">Reunião</button>
                <button onClick={() => applyPreset('operator')} className="p-2 border border-slate-300 rounded text-center bg-emerald-50 hover:bg-emerald-100 font-bold text-[10px]">Técnico</button>
              </div>
            </div>

            {/* TEMA E LAYOUT */}
            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-slate-600">Tema Visual</label>
                <select 
                  value={settings.theme} 
                  onChange={(e) => updateSetting('theme', e.target.value)} 
                  className="w-full p-2 border rounded"
                >
                  <option value="dark">Tema Escuro (Original)</option>
                  <option value="light">Tema Claro (Corporativo)</option>
                  <option value="factory">TV Fábrica (Alto Contraste Claro)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-600">Modo / Layout</label>
                <select 
                  value={settings.layout} 
                  onChange={(e) => updateSetting('layout', e.target.value)} 
                  className="w-full p-2 border rounded"
                >
                  {(Object.keys(layoutLabels) as TVLayout[]).map(lay => (
                    <option key={lay} value={lay}>{layoutLabels[lay]}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-600">Tamanho da Fonte</label>
                <select 
                  value={settings.fontSize} 
                  onChange={(e) => updateSetting('fontSize', e.target.value)} 
                  className="w-full p-2 border rounded"
                >
                  <option value="small">Pequeno</option>
                  <option value="medium">Médio</option>
                  <option value="large">Grande</option>
                  <option value="xlarge">Extra Grande (Fábrica)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-600">Densidade Espaçamento</label>
                <select 
                  value={settings.density} 
                  onChange={(e) => updateSetting('density', e.target.value)} 
                  className="w-full p-2 border rounded"
                >
                  <option value="compact">Compacto</option>
                  <option value="medium">Médio</option>
                  <option value="factory">Fábrica (Espaçado)</option>
                </select>
              </div>
            </div>

            {/* AUTO SCROLL E PAGINAÇÃO */}
            <div className="space-y-4 border-t pt-4">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="autoScroll_chk"
                  checked={settings.autoScroll} 
                  onChange={(e) => updateSetting('autoScroll', e.target.checked)} 
                  className="w-4 h-4"
                />
                <label htmlFor="autoScroll_chk" className="cursor-pointer">Auto-scroll de Páginas</label>
              </div>

              {settings.autoScroll && (
                <div className="space-y-1">
                  <label className="text-slate-600">Velocidade de rotação (segundos)</label>
                  <input 
                    type="number" 
                    value={settings.autoScrollSeconds} 
                    onChange={(e) => updateSetting('autoScrollSeconds', Number(e.target.value))} 
                    className="w-full p-2 border rounded"
                    min={5}
                  />
                </div>
              )}

              <div className="space-y-1">
                <label className="text-slate-600">Linhas por página (para 16+ itens)</label>
                <input 
                  type="number" 
                  value={settings.visibleRows} 
                  onChange={(e) => updateSetting('visibleRows', Number(e.target.value))} 
                  className="w-full p-2 border rounded"
                  min={1}
                />
              </div>
            </div>

            {/* EXIBIÇÃO DE COMPONENTES */}
            <div className="space-y-2 border-t pt-4">
              <span className="block text-slate-500 text-[10px] uppercase font-black">Elementos Visíveis</span>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { key: 'showClock', label: 'Relógio' },
                  { key: 'showBoardName', label: 'Nome Board' },
                  { key: 'showLayoutName', label: 'Layout atual' },
                  { key: 'showKpis', label: 'KPIs Métrica' },
                  { key: 'showRanking', label: 'Ranking Crítico' },
                  { key: 'showExitButton', label: 'Botão Sair' },
                  { key: 'showDescription', label: 'Descrição' },
                  { key: 'showAssignees', label: 'Técnico/Responsável' },
                  { key: 'showLabels', label: 'Etiquetas' },
                ].map(el => (
                  <div key={el.key} className="flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      id={`chk_${el.key}`} 
                      checked={(settings as any)[el.key]} 
                      onChange={(e) => updateSetting(el.key as any, e.target.checked)} 
                    />
                    <label htmlFor={`chk_${el.key}`} className="cursor-pointer text-[10px]">{el.label}</label>
                  </div>
                ))}
              </div>
            </div>

            {/* FILTRO DE COLUNAS */}
            <div className="space-y-2 border-t pt-4">
              <span className="block text-slate-500 text-[10px] uppercase font-black">Ocultar Colunas</span>
              <div className="space-y-1 max-h-32 overflow-y-auto border p-2 rounded bg-slate-50">
                {data.columns.map(col => {
                  const isHidden = settings.hiddenColumns.includes(col.id);
                  return (
                    <div key={col.id} className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        id={`hide_col_${col.id}`}
                        checked={isHidden}
                        onChange={(e) => {
                          const updated = e.target.checked 
                            ? [...settings.hiddenColumns, col.id] 
                            : settings.hiddenColumns.filter(id => id !== col.id);
                          updateSetting('hiddenColumns', updated);
                        }} 
                      />
                      <label htmlFor={`hide_col_${col.id}`} className="cursor-pointer text-[10px]">{col.name}</label>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* FILTRO DE CAMPOS */}
            <div className="space-y-2 border-t pt-4">
              <span className="block text-slate-500 text-[10px] uppercase font-black">Ocultar Campos (TV Lista)</span>
              <div className="space-y-1 max-h-32 overflow-y-auto border p-2 rounded bg-slate-50">
                {[
                  { key: 'title', label: 'Título/Tarefa' },
                  { key: 'due_date', label: 'Prazo' },
                  ...(data.board.custom_fields || []).map((f: any) => ({ key: f.key, label: f.name }))
                ].map(f => {
                  const isHidden = settings.hiddenFields.includes(f.key);
                  return (
                    <div key={f.key} className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        id={`hide_f_${f.key}`}
                        checked={isHidden}
                        onChange={(e) => {
                          const updated = e.target.checked 
                            ? [...settings.hiddenFields, f.key] 
                            : settings.hiddenFields.filter(key => key !== f.key);
                          updateSetting('hiddenFields', updated);
                        }} 
                      />
                      <label htmlFor={`hide_f_${f.key}`} className="cursor-pointer text-[10px]">{f.label}</label>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t mt-6">
            <button 
              className="w-full py-2 bg-slate-900 text-white rounded text-[10px] hover:bg-slate-800"
              onClick={() => setShowConfig(false)}
            >
              Confirmar Ajustes
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const TVList = ({ 
  cards, 
  fields, 
  production, 
  settings, 
  columns, 
  customFields
}: { 
  cards: KanbanCard[]; 
  fields: string[]; 
  production?: boolean; 
  settings: LocalSettings; 
  columns: any[]; 
  customFields: any[];
}) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  
  const visible = fields && fields.length > 0 ? fields : ['title', 'due_date'];
  const visibleRows = Number(settings.visibleRows || 16);
  const totalPages = Math.ceil(cards.length / visibleRows);

  useEffect(() => {
    if (!settings.autoScroll || totalPages <= 1 || isPaused) return;
    const timer = setInterval(() => {
      setCurrentPage((prev) => (prev + 1) % totalPages);
    }, settings.autoScrollSeconds * 1000);
    return () => clearInterval(timer);
  }, [settings.autoScroll, totalPages, isPaused, settings.autoScrollSeconds]);

  useEffect(() => {
    setCurrentPage(0);
  }, [cards.length, visibleRows]);

  const startIndex = currentPage * visibleRows;
  const rows = cards.slice(startIndex, startIndex + visibleRows);
  const isFactory = settings.theme === 'factory';

  // Estilo de Fonte
  const fontSize = settings.fontSize === 'xlarge' ? 24 : settings.fontSize === 'large' ? 20 : settings.fontSize === 'small' ? 13 : 16;
  const rowHeight = settings.density === 'factory' ? 56 : settings.density === 'compact' ? 38 : 46;

  const getRowStyle = (card: KanbanCard) => {
    const col = columns.find((c) => c.id === card.column_id);
    const colColor = col?.color;
    const baseColor = colColor ? colColor.split(';')[0] : '';
    
    if (isFactory) {
      // Alto Contraste Claro da Fábrica
      return {
        background: card.priority === 'URGENT' ? '#fee2e2' : '#ffffff',
        borderLeft: baseColor ? `6px solid ${baseColor}` : '6px solid #0f172a',
        color: '#0f172a'
      };
    }

    // Cores originais escuras
    if (baseColor) {
      return {
        background: 'rgba(15, 23, 42, 0.84)',
        borderLeft: `5px solid ${baseColor}`,
        color: '#cbd5e1'
      };
    }
    
    return {
      background: 'rgba(59, 130, 246, 0.10)',
      borderLeft: '5px solid #3b82f6',
      color: '#dbeafe'
    };
  };

  return (
    <div 
      onMouseEnter={() => setIsPaused(true)} 
      onMouseLeave={() => setIsPaused(false)}
      style={{ width: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
    >
      <table className={isFactory ? 'tv-factory-table' : undefined} style={isFactory ? undefined : { width: '100%', borderCollapse: 'separate', borderSpacing: '0 8px' }}>
        <thead>
          <tr>
            {visible.map((colKey) => {
              const header = colKey === 'title' ? 'Tarefa' : colKey === 'due_date' ? 'Prazo' : (customFields.find(cf => cf.key === colKey)?.name || colKey);
              return (
                <th 
                  key={colKey} 
                  className={isFactory ? 'tv-factory-th' : undefined}
                  style={isFactory ? undefined : { color: '#94a3b8', fontWeight: 800, textTransform: 'uppercase', fontSize: '12px', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}
                >
                  {header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((card) => {
            const rowStyle = getRowStyle(card);
            const isUrgent = card.priority === 'URGENT';
            return (
              <tr 
                key={card.id} 
                className={isFactory ? `tv-factory-tr ${isUrgent ? 'critical' : ''}` : undefined}
                style={isFactory ? undefined : { 
                  backgroundColor: rowStyle.background,
                  outline: isUrgent ? '2px solid rgba(239, 68, 68, 0.5)' : undefined 
                }}
              >
                {visible.map((colKey, colIdx) => {
                  const isFirst = colIdx === 0;
                  const isTitle = colKey === 'title';
                  
                  return (
                    <td 
                      key={colKey} 
                      className={isFactory ? 'tv-factory-td' : undefined}
                      style={{ 
                        borderLeft: (isFirst && !isFactory) ? rowStyle.borderLeft : undefined,
                        height: rowHeight, 
                        fontSize: isTitle ? fontSize + 2 : fontSize, 
                        padding: '12px',
                        fontWeight: isTitle ? 900 : 700, 
                        color: isFactory ? '#0f172a' : rowStyle.color,
                        borderBottom: isFactory ? undefined : '1px solid rgba(30, 41, 59, 0.3)'
                      }}
                    >
                      {isTitle ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          {production && (card.custom_fields as any)?.op && (
                            <span className={isFactory ? 'tv-factory-card-op block' : undefined} style={isFactory ? undefined : { color: '#38bdf8', fontWeight: 900, fontSize: '11px' }}>
                              OP {String((card.custom_fields as any).op)}
                            </span>
                          )}
                          <span>{card.title}</span>
                          {settings.showDescription && card.description && (
                            <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 650, display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              {card.description}
                            </span>
                          )}
                        </div>
                      ) : colKey === 'due_date' ? (
                        card.due_date ? new Date(card.due_date).toLocaleDateString('pt-BR') : '-'
                      ) : (
                        String(card.custom_fields?.[colKey] ?? '-')
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: '#94a3b8', fontWeight: 700, padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }}>
          <span>Mostrando {startIndex + 1}–{Math.min(startIndex + visibleRows, cards.length)} de {cards.length}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span>Página {currentPage + 1} de {totalPages}</span>
            <button onClick={() => setIsPaused(!isPaused)} style={{ padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
              {isPaused ? <Play size={12} style={{ color: '#22c55e' }} /> : <Pause size={12} style={{ color: '#f59e0b' }} />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const ColumnsLayout = ({ columns, cards, settings }: { columns: any[]; cards: KanbanCard[]; settings: LocalSettings }) => {
  const isFactory = settings.theme === 'factory';
  return (
    <div className={isFactory ? 'tv-factory-columns-container' : undefined} style={isFactory ? undefined : { display: 'flex', gap: '16px', alignItems: 'flex-start', overflowX: 'auto', width: '100%', paddingBottom: '16px' }}>
      {columns.map((column) => {
        const colColor = column.color;
        const baseColor = colColor ? colColor.split(';')[0] : '';
        const isComplete = colColor?.endsWith(';complete');
        const colCards = cards.filter(c => c.column_id === column.id);

        return (
          <section 
            key={column.id} 
            className={isFactory ? 'tv-factory-column' : undefined}
            style={isFactory ? undefined : { 
              minWidth: '280px',
              padding: '12px',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              background: 'rgba(15, 23, 42, 0.6)', 
              borderTop: baseColor ? `4px solid ${baseColor}` : '1px solid rgba(255, 255, 255, 0.08)' 
            }}
          >
            <h2 className={isFactory ? 'tv-factory-column-title' : undefined} style={isFactory ? undefined : { color: '#f8fafc', fontWeight: 900, fontSize: '14px', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{column.name}</span>
              <span style={{ color: '#64748b', fontWeight: 800 }}>{colCards.length}</span>
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {colCards.map((card) => (
                <TVCard key={card.id} card={card} settings={settings} baseColor={baseColor} isComplete={isComplete} />
              ))}
              {colCards.length === 0 && (
                <div style={{ textAlign: 'center', padding: '24px 0', fontSize: '11px', color: '#64748b', fontWeight: 700 }}>Vazio</div>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
};

const UrgencyLayout = ({ cards, isFactory }: { cards: KanbanCard[]; isFactory?: boolean }) => {
  const crit = cards.filter((card) => Number(card.urgency_score || 0) >= 70);
  const warn = cards.filter((card) => Number(card.urgency_score || 0) >= 25 && Number(card.urgency_score || 0) < 70);
  const norm = cards.filter((card) => Number(card.urgency_score || 0) < 25);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[
        { title: '🚨 Crítico', items: crit, color: 'bg-red-500' },
        { title: '⚠️ Atenção', items: warn, color: 'bg-amber-500' },
        { title: '✅ Normal', items: norm, color: 'bg-green-500' },
      ].map((sec) => (
        <section 
          key={sec.title} 
          className={isFactory ? 'tv-factory-column min-h-[400px]' : 'bg-slate-900 border border-slate-800 p-3 rounded-xl min-h-[400px] flex flex-col gap-3'}
        >
          <h2 className={isFactory ? 'tv-factory-column-title' : 'text-slate-100 font-black text-sm uppercase border-b pb-2'}>
            <span>{sec.title}</span>
            <span className="text-slate-500 font-bold">{sec.items.length}</span>
          </h2>
          <div className="space-y-2">
            {sec.items.map(card => (
              <article 
                key={card.id} 
                className={isFactory ? 'tv-factory-card' : 'bg-slate-950 p-3 rounded border border-slate-800'}
              >
                <div className="font-extrabold text-xs text-slate-800">{card.title}</div>
                <div className="text-[10px] text-slate-500 font-bold">Urgência: {card.urgency_score} pts</div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
};

const TVCard = ({ 
  card, 
  settings, 
  baseColor, 
  isComplete 
}: { 
  card: KanbanCard; 
  settings: LocalSettings; 
  baseColor?: string; 
  isComplete?: boolean;
}) => {
  const isFactory = settings.theme === 'factory';
  return (
    <article 
      className={isFactory ? 'tv-factory-card' : undefined}
      style={isFactory ? undefined : {
        padding: '12px',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.06)',
        background: isComplete && baseColor ? `${baseColor}1E` : 'rgba(2, 6, 23, 0.8)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {!isFactory && !isComplete && baseColor && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, backgroundColor: baseColor }} />
      )}
      {(card.custom_fields as any)?.op && (
        <div className={isFactory ? 'tv-factory-card-op' : undefined} style={isFactory ? undefined : { color: '#38bdf8', fontWeight: 900, fontSize: '11px' }}>
          OP {String((card.custom_fields as any).op)}
        </div>
      )}
      <h3 className={isFactory ? 'tv-factory-card-title' : undefined} style={isFactory ? undefined : { color: '#e2e8f0', fontWeight: 900, fontSize: '14px', marginTop: '4px', margin: 0 }}>
        {card.title}
      </h3>
      {settings.showDescription && card.description && (
        <p style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600, marginTop: '4px', margin: 0, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {card.description}
        </p>
      )}
      {card.due_date && (
        <p className={isFactory ? 'tv-factory-card-due' : undefined} style={isFactory ? undefined : { color: '#f87171', fontSize: '11px', fontWeight: 700, marginTop: '8px', margin: 0 }}>
          Prazo: {new Date(card.due_date).toLocaleDateString('pt-BR')}
        </p>
      )}
    </article>
  );
};

const Metric = ({ label, value, danger, isFactory }: { label: string; value: number; danger?: boolean; isFactory?: boolean }) => {
  if (isFactory) {
    return (
      <div className={`tv-factory-metric ${danger ? 'danger' : ''}`}>
        <div className="tv-factory-metric-label">{label}</div>
        <strong className="tv-factory-metric-value">{value}</strong>
      </div>
    );
  }
  return (
    <div style={{
      padding: '12px 16px',
      borderRadius: '12px',
      border: danger ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
      backgroundColor: danger ? 'rgba(239, 68, 68, 0.08)' : 'rgba(255, 255, 255, 0.03)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px'
    }}>
      <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
      <strong style={{ color: danger ? '#f87171' : '#f8fafc', fontSize: '24px', fontWeight: 900 }}>{value}</strong>
    </div>
  );
};

const tvRoot: React.CSSProperties = { minHeight: '100vh', background: '#020617', color: '#e2e8f0', padding: 20, display: 'flex', flexDirection: 'column' };
const tvHeader: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, borderBottom: '1px solid rgba(148,163,184,0.18)', paddingBottom: 14 };
const metricRow: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(5, minmax(140px, 1fr))', gap: 12, marginTop: 16 };

