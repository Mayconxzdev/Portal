import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Clock,
  Copy,
  Eye,
  FileKey,
  HardDrive,
  KeyRound,
  Laptop,
  Lock,
  MessageSquare,
  Network,
  Paperclip,
  Play,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  TimerReset,
  Kanban,
  UserCircle,
  Wrench,
  X,
  Plus,
  Trash2,
  Archive,
  Save,
  FileSpreadsheet,
  Upload,
  Download,
  CheckCircle,
  StickyNote,
  Settings,
  Mail,
  Database,
  Info,
  List,
  ArrowRight,
  UserCheck,
  History,
  AlertCircle
} from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { Input } from '../components/ui/Input';
import { LoadingState } from '../components/ui/LoadingState';
import { Modal } from '../components/ui/Modal';
import { Drawer } from '../components/ui/Drawer';
import { Select } from '../components/ui/Select';
import { Textarea } from '../components/ui/Textarea';
import { ModuleHero } from '../components/ui/ModuleHero';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { ITOverview } from '../components/it/ITOverview';
import { ITTickets } from '../components/it/ITTickets';
import { ITAssets } from '../components/it/ITAssets';
import { ITCredentials } from '../components/it/ITCredentials';
import { ITCertificates } from '../components/it/ITCertificates';
import { ITNetwork } from '../components/it/ITNetwork';
import { ITMaintenance } from '../components/it/ITMaintenance';
import { ITNotes } from '../components/it/ITNotes';
import { ITReports } from '../components/it/ITReports';
import { ITSettings } from '../components/it/ITSettings';
import { FooterStatusBar } from '../components/ui/FooterStatusBar';
import { CreateTicketModal } from '../components/it/CreateTicketModal';
import {
  categoryLabel,
  categoryOptions,
  itRequest,
  ITSummary,
  ITTicket,
  priorityLabel,
  priorityLabels,
  statusLabel
} from '../components/it/itApi';
import { isTauriApp, collectLocalPcInventory, getDesktopEnvironment } from '../utils/tauri';
import { AdminRealDataDashboard } from '../components/legacy-import/AdminRealDataDashboard';

interface ITPageProps {
  currentUser?: any;
}

type TabKey =
  | 'overview'
  | 'tickets'
  | 'assets'
  | 'access_credentials'
  | 'access_matrix'
  | 'certificates_licenses'
  | 'network_nas'
  | 'maintenance'
  | 'notes'
  | 'reports'
  | 'settings';

interface QueueFilters {
  q: string;
  ticket_number: string;
  requester_user_id: string;
  assigned_to_user_id: string;
  status: string;
  category: string;
  priority: string;
  sla_state: string;
  unassigned: boolean;
  assigned_to_me: boolean;
  created_today: boolean;
  recently_updated: boolean;
  has_attachments: boolean;
  has_kanban_card: boolean;
  missing_kanban_card: boolean;
  sort_by: string;
  sort_dir: string;
}

const emptyFilters: QueueFilters = {
  q: '',
  ticket_number: '',
  requester_user_id: '',
  assigned_to_user_id: '',
  status: '',
  category: '',
  priority: '',
  sla_state: '',
  unassigned: false,
  assigned_to_me: false,
  created_today: false,
  recently_updated: false,
  has_attachments: false,
  has_kanban_card: false,
  missing_kanban_card: false,
  sort_by: 'recentes',
  sort_dir: 'desc',
};

const statusOptions = [
  { value: 'ABERTO', label: 'Aberto' },
  { value: 'EM_ATENDIMENTO', label: 'Em atendimento' },
  { value: 'SUSPENSO', label: 'Suspenso' },
  { value: 'FECHADO', label: 'Fechado' },
];

const priorityOptions = [
  { value: 'BAIXA', label: 'Baixa' },
  { value: 'MEDIA', label: 'Média' },
  { value: 'ALTA', label: 'Alta' },
  { value: 'CRITICA', label: 'Crítica' },
];

const POWERSHELL_COLLECT_SCRIPT = `# Script de Coleta Manual de Inventario do PC - Portal Vesper
try {
    $Output = @{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        os_version = (Get-CimInstance Win32_OperatingSystem).Version
        manufacturer = (Get-CimInstance Win32_ComputerSystem).Manufacturer
        model = (Get-CimInstance Win32_ComputerSystem).Model
        serial_number = (Get-CimInstance Win32_BIOS).SerialNumber
        processor = (Get-CimInstance Win32_Processor).Name
        ram_total = "$([math]::round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB)) GB"
        motherboard = "$((Get-CimInstance Win32_BaseBoard).Manufacturer) - $((Get-CimInstance Win32_BaseBoard).Product)"
        gpu = (Get-CimInstance Win32_VideoController).Name -join ", "
        storage = (Get-CimInstance Win32_DiskDrive | ForEach-Object { "$($_.Model) ($([math]::round($_.Size / 1GB))) GB" }) -join ", "
        ip_address = (Get-NetIPAddress -InterfaceAddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
        mac_address = (Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1).MacAddress
        domain = (Get-CimInstance Win32_ComputerSystem).Domain
        date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    $Filename = "pc-inventory-$($Output.hostname).json"
    $Json = $Output | ConvertTo-Json
    $Path = Join-Path $env:USERPROFILE "Desktop\\$Filename"
    $Json | Out-File -FilePath $Path -Encoding utf8
    Write-Host "COLETA CONCLUIDA COM SUCESSO!" -ForegroundColor Green
    Write-Host "Salvo no Desktop: $Path" -ForegroundColor Cyan
} catch {
    Write-Error "Erro: $_"
}`;

const withEmpty = (options: { value: string; label: string }[], label = 'Todos') => [{ value: '', label }, ...options];

const assetStatusLabel = (status?: string) => ({
  DISPONIVEL: 'Disponível',
  EM_USO: 'Em uso',
  MANUTENCAO: 'Em manutenção',
  APOSENTADO: 'Aposentado',
  PERDIDO: 'Perdido',
}[String(status || '').toUpperCase()] || status || 'Não informado');

const maintenanceStatusLabel = (status?: string) => ({
  AGENDADA: 'Agendada',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDA: 'Concluída',
  CANCELADA: 'Cancelada',
}[String(status || '').toUpperCase()] || status || 'Não informado');

const fieldLabel = (field?: string) => ({
  name: 'Nome',
  hostname: 'Hostname',
  asset_tag: 'Patrimônio',
  serial_number: 'Número de série',
  status: 'Status',
  processor: 'Processador',
  ram: 'Memória RAM',
  storage: 'Armazenamento',
  ip_address: 'Endereço IP',
  user_id: 'Usuário vinculado',
}[String(field || '')] || field || 'registro');

function buildTicketQuery(filters: QueueFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (typeof value === 'boolean') {
      if (value) params.set(key, 'true');
      return;
    }
    if (value) params.set(key, String(value));
  });
  return params.toString();
}

export const ITPage: React.FC<ITPageProps> = ({ currentUser }) => {
  const [customCategories, setCustomCategories] = useState<any[]>(() => {
    const saved = localStorage.getItem('vesper.it.custom_categories');
    return saved ? JSON.parse(saved) : [];
  });
  const [customAssetTypes, setCustomAssetTypes] = useState<any[]>(() => {
    const saved = localStorage.getItem('vesper.it.custom_asset_types');
    return saved ? JSON.parse(saved) : [];
  });

  const activeCategories = useMemo(() => [
    ...categoryOptions,
    ...customCategories.filter(c => c.is_active)
  ], [customCategories]);

  const activeAssetTypes = useMemo(() => [
    { value: 'PC', label: 'Computador/Desktop' },
    { value: 'NOTEBOOK', label: 'Notebook' },
    { value: 'MONITOR', label: 'Monitor' },
    { value: 'IMPRESSORA', label: 'Impressora' },
    { value: 'SERVIDOR', label: 'Servidor' },
    { value: 'ROTEADOR', label: 'Roteador' },
    { value: 'SWITCH', label: 'Switch' },
    { value: 'OUTRO', label: 'Outro' },
    ...customAssetTypes.filter(t => t.is_active)
  ], [customAssetTypes]);

  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [summary, setSummary] = useState<ITSummary | null>(null);
  const [tickets, setTickets] = useState<ITTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<ITTicket | null>(null);
  const [queueFilters, setQueueFilters] = useState<QueueFilters>(emptyFilters);
  const [createOpen, setCreateOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: async () => {},
  });

  // Modais extras da Fase 5.2
  const [collectModalOpen, setCollectModalOpen] = useState(false);
  const [collectLoading, setCollectLoading] = useState(false);
  const [collectedSpecs, setCollectedSpecs] = useState<any>(null);
  const [previewDiff, setPreviewDiff] = useState<any>(null);
  const [selectedFieldsToApply, setSelectedFieldsToApply] = useState<string[]>([]);
  const [selectedAssetForSpecs, setSelectedAssetForSpecs] = useState<number | null>(null);

  // Mapeamento manual / fallback JSON
  const [manualJsonText, setManualJsonText] = useState('');
  const [jsonImportOpen, setJsonImportOpen] = useState(false);

  // Importação CSV de ativos
  const [csvImportOpen, setCsvImportOpen] = useState(false);
  const [csvContent, setCsvContent] = useState('');
  const [csvPreview, setCsvPreview] = useState<any[]>([]);
  const [csvUpdateExisting, setCsvUpdateExisting] = useState(true);

  // Detalhe Completo do Ativo
  const [selectedAsset, setSelectedAsset] = useState<any | null>(null);
  const [assetHistory, setAssetHistory] = useState<any[]>([]);
  const [assetFormOpen, setAssetFormOpen] = useState(false);
  const [assetForm, setAssetForm] = useState<any>({});
  const [activeAssetDetailTab, setActiveAssetDetailTab] = useState<string>('resumo');

  // Listagem de outros recursos
  const [people, setPeople] = useState<any[]>([]);
  const [customFields, setCustomFields] = useState<any[]>([]);
  const [corporateEmails, setCorporateEmails] = useState<any[]>([]);
  const [nasFolders, setNasFolders] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [changeLogs, setChangeLogs] = useState<any[]>([]);
  const [assetsList, setAssetsList] = useState<any[]>([]);
  const [certificates, setCertificates] = useState<any[]>([]);
  const [networkItems, setNetworkItems] = useState<any[]>([]);
  const [maintenances, setMaintenances] = useState<any[]>([]);

  // Modais de Criação de Entidades
  const [genericModalOpen, setGenericModalOpen] = useState<string | null>(null); // 'email' | 'nas' | 'note' | 'custom_field' | 'asset' | 'certificate' | 'network' | 'maintenance'
  const [assetToRetire, setAssetToRetire] = useState<number | null>(null);
  const [genericForm, setGenericForm] = useState<any>({});

  const itLevel = currentUser?.module_permissions?.it || (currentUser?.role === 'ADMIN' ? 'ADMIN' : 'NO_ACCESS');
  const isStaff = currentUser?.role === 'ADMIN' || ['MANAGER', 'ADMIN'].includes(itLevel);

  // Forçar aba de tickets para usuário comum
  useEffect(() => {
    if (!isStaff) {
      setActiveTab('tickets');
    }
  }, [isStaff]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const queueQuery = buildTicketQuery(queueFilters);
      const ticketPath = isStaff ? `/tickets${queueQuery ? `?${queueQuery}` : ''}` : '/tickets?mine=true';
      const [summaryData, ticketData] = await Promise.all([
        itRequest<ITSummary>('/summary'),
        itRequest<ITTicket[]>(ticketPath),
      ]);
      setSummary(summaryData);
      setTickets(ticketData);

      if (isStaff) {
        // Carrega dados adicionais da Fase 5.2
        const [
          assetsData,
          peopleData,
          emailsData,
          nasData,
          notesData,
          logsData,
          fieldsData,
          certsData,
          netData,
          maintData
        ] = await Promise.all([
          itRequest<any[]>('/assets'),
          itRequest<any[]>('/people').catch(() => []),
          itRequest<any[]>('/corporate-emails').catch(() => []),
          itRequest<any[]>('/nas').catch(() => []),
          itRequest<any[]>('/notes').catch(() => []),
          itRequest<any[]>('/change-log').catch(() => []),
          itRequest<any[]>('/asset-fields').catch(() => []),
          itRequest<any[]>('/certificates').catch(() => []),
          itRequest<any[]>('/network-items').catch(() => []),
          itRequest<any[]>('/maintenance-records').catch(() => [])
        ]);
        setAssetsList(assetsData);
        setPeople(peopleData);
        setCorporateEmails(emailsData);
        setNasFolders(nasData);
        setNotes(notesData);
        setChangeLogs(logsData);
        setCustomFields(fieldsData);
        setCertificates(certsData);
        setNetworkItems(netData);
        setMaintenances(maintData);
      }
    } catch (err: any) {
      setError(err.message || 'Não foi possível carregar o módulo TI.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 30000);
    return () => window.clearInterval(interval);
  }, [isStaff, queueFilters]);

  // WebSocket Integration
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/it`);
    const ping = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send('ping');
    }, 25000);
    socket.onmessage = (event) => {
      if (event.data !== 'pong') load();
    };
    return () => {
      window.clearInterval(ping);
      socket.close();
    };
  }, [isStaff, queueFilters]);

  const openTicket = async (ticket: ITTicket) => {
    const detail = await itRequest<ITTicket>(`/tickets/${ticket.id}`);
    setSelectedTicket(detail);
  };

  const refreshTicket = async () => {
    if (!selectedTicket) return;
    const detail = await itRequest<ITTicket>(`/tickets/${selectedTicket.id}`);
    setSelectedTicket(detail);
    await load();
  };

  // Coleta Tauri Local
  const handleCollectLocal = async () => {
    setCollectLoading(true);
    setError('');
    try {
      const data = await collectLocalPcInventory();
      if (!data) {
        throw new Error("Não foi possível coletar dados. Certifique-se de que está rodando no Tauri.");
      }
      setCollectedSpecs(data);
      // Solicita preview ao backend
      const preview = await itRequest<any>('/assets/specs/preview', {
        method: 'POST',
        body: JSON.stringify(data)
      });
      setPreviewDiff(preview);
      setSelectedAssetForSpecs(preview.asset?.id || null);
      // Por padrão seleciona todos os campos de diff para aplicar
      setSelectedFieldsToApply((preview.diffs || []).map((d: any) => d.field));
      setCollectModalOpen(true);
    } catch (err: any) {
      setError(err.message || "Erro de coleta nativa.");
    } finally {
      setCollectLoading(false);
    }
  };

  // Coleta Fallback manual
  const handleJsonImport = async () => {
    setError('');
    try {
      const parsed = JSON.parse(manualJsonText);
      const preview = await itRequest<any>('/assets/specs/preview', {
        method: 'POST',
        body: JSON.stringify(parsed)
      });
      setCollectedSpecs(parsed);
      setPreviewDiff(preview);
      setSelectedAssetForSpecs(preview.asset?.id || null);
      setSelectedFieldsToApply((preview.diffs || []).map((d: any) => d.field));
      setJsonImportOpen(false);
      setCollectModalOpen(true);
    } catch (err: any) {
      setError("JSON inválido ou erro no processamento das especificações.");
    }
  };

  // Confirmar especificações coletadas
  const handleConfirmSpecs = async () => {
    if (!previewDiff) return;
    try {
      const payload = {
        asset_id: selectedAssetForSpecs,
        hostname: collectedSpecs.hostname || previewDiff.collected_data?.hostname || "HostnameDesconhecido",
        username: collectedSpecs.username || previewDiff.collected_data?.username,
        os: collectedSpecs.os || previewDiff.collected_data?.os,
        os_version: collectedSpecs.os_version || previewDiff.collected_data?.os_version,
        manufacturer: collectedSpecs.manufacturer || previewDiff.collected_data?.manufacturer,
        model: collectedSpecs.model || previewDiff.collected_data?.model,
        serial_number: collectedSpecs.serial_number || previewDiff.collected_data?.serial_number,
        processor: collectedSpecs.processor || previewDiff.collected_data?.processor,
        ram: collectedSpecs.ram_total || previewDiff.collected_data?.ram_total,
        motherboard: collectedSpecs.motherboard || previewDiff.collected_data?.motherboard,
        gpu: collectedSpecs.gpu || previewDiff.collected_data?.gpu,
        storage: collectedSpecs.storage || previewDiff.collected_data?.storage,
        ip_address: collectedSpecs.ip_address || previewDiff.collected_data?.ip_address,
        apply_fields: selectedFieldsToApply
      };

      await itRequest('/assets/specs/confirm', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setMessage("Especificações integradas ao ativo com sucesso!");
      setCollectModalOpen(false);
      load();
    } catch (err: any) {
      setError(err.message || "Erro ao aplicar especificações.");
    }
  };

  // Preview de CSV
  const handleCSVPreview = async () => {
    if (!csvContent.trim()) return;
    try {
      const lines = csvContent.split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      const assetsListParsed: any[] = [];
      for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue;
        const cols = lines[i].split(',').map(c => c.trim());
        const assetObj: any = { name: "" };
        headers.forEach((h, index) => {
          if (cols[index]) {
            assetObj[h] = cols[index];
          }
        });
        if (assetObj.name) {
          assetsListParsed.push(assetObj);
        }
      }

      const previewRes = await itRequest<{ assets: any[] }>('/assets/import/preview', {
        method: 'POST',
        body: JSON.stringify(assetsListParsed)
      });
      setCsvPreview(previewRes.assets || []);
    } catch (err: any) {
      setError("Erro ao gerar preview do CSV. Verifique o cabeçalho e separadores.");
    }
  };

  // Confirmar Importação CSV
  const handleCSVConfirm = async () => {
    try {
      await itRequest('/assets/import/confirm', {
        method: 'POST',
        body: JSON.stringify({
          assets: csvPreview,
          update_existing: csvUpdateExisting
        })
      });
      setMessage(`${csvPreview.length} ativos importados com sucesso!`);
      setCsvImportOpen(false);
      setCsvContent('');
      setCsvPreview([]);
      load();
    } catch (err: any) {
      setError(err.message || "Erro na importação.");
    }
  };

  // Visualizar ficha detalhada do ativo
  const handleOpenAssetDetail = async (asset: any) => {
    setSelectedAsset(asset);
    setActiveAssetDetailTab('resumo');
    try {
      const history = await itRequest<any[]>(`/assets/${asset.id}/history`);
      setAssetHistory(history);
    } catch {
      setAssetHistory([]);
    }
  };

  // Salvar edições do ativo
  const handleSaveAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (assetForm.id) {
        await itRequest(`/assets/${assetForm.id}`, {
          method: 'PATCH',
          body: JSON.stringify(assetForm)
        });
        setMessage("Ativo atualizado!");
      } else {
        await itRequest('/assets', {
          method: 'POST',
          body: JSON.stringify(assetForm)
        });
        setMessage("Ativo cadastrado!");
      }
      setAssetFormOpen(false);
      setSelectedAsset(null);
      load();
    } catch (err: any) {
      setError(err.message || "Erro ao salvar ativo.");
    }
  };

  // Salvar nota (Sticky Note)
  const handleSaveNote = async (notePayload: any) => {
    try {
      if (notePayload.id) {
        await itRequest(`/notes/${notePayload.id}`, {
          method: 'PATCH',
          body: JSON.stringify(notePayload)
        });
      } else {
        await itRequest('/notes', {
          method: 'POST',
          body: JSON.stringify(notePayload)
        });
      }
      load();
    } catch (err: any) {
      setError("Erro ao salvar nota.");
    }
  };

  // Arquivar nota
  const handleArchiveNote = async (id: number) => {
    try {
      await itRequest(`/notes/${id}/archive`, { method: 'POST' });
      load();
    } catch {
      setError("Erro ao arquivar nota.");
    }
  };

  // CRUD de outras entidades
  const handleGenericSave = async () => {
    if (!genericModalOpen) return;
    let endpoint = "";
    if (genericModalOpen === 'email') endpoint = "/corporate-emails";
    if (genericModalOpen === 'nas') endpoint = "/nas";
    if (genericModalOpen === 'vault') endpoint = "/credentials";
    if (genericModalOpen === 'accessCatalog') endpoint = "/access-catalog";
    if (genericModalOpen === 'custom_field') endpoint = "/asset-fields";
    if (genericModalOpen === 'certificate') endpoint = "/certificates";
    if (genericModalOpen === 'network') endpoint = "/network-items";
    if (genericModalOpen === 'maintenance') endpoint = "/maintenance-records";

    try {
      const method = genericForm.id ? 'PATCH' : 'POST';
      const path = genericForm.id ? `${endpoint}/${genericForm.id}` : endpoint;
      await itRequest(path, {
        method,
        body: JSON.stringify(genericForm)
      });
      setMessage("Registro salvo!");
      setGenericModalOpen(null);
      setGenericForm({});
      load();
    } catch (err: any) {
      setError(err.message || "Erro ao salvar registro.");
    }
  };

  // Exclusão/Retirada segura
  const confirmRetireAsset = async (id: number) => {
    try {
      await itRequest(`/assets/${id}/retire`, { method: 'POST' });
      setMessage("Ativo aposentado e arquivado com sucesso!");
      setSelectedAsset(null);
      load();
    } catch (err: any) {
      setError(err.message || "Erro ao aposentar ativo.");
    }
  };

  const handleRetireAsset = async (id: number) => {
    setAssetToRetire(id);
  };

  const handleDeleteRecord = (endpoint: string, id: number, entityLabel: string, recordName: string) => {
    setDeleteConfirm({
      isOpen: true,
      title: `Excluir ${entityLabel}`,
      message: `Deseja realmente excluir permanentemente o registro "${recordName}"? Esta ação é irreversível.`,
      onConfirm: async () => {
        try {
          await itRequest(`${endpoint}/${id}`, { method: 'DELETE' });
          setMessage(`${entityLabel} excluído com sucesso.`);
          load();
        } catch (err: any) {
          setError(err.message || `Erro ao excluir ${entityLabel}.`);
        }
      }
    });
  };

  // Exportar Relatórios CSV
  const handleExportCSV = (entity: string) => {
    window.open(`/api/v1/it/reports/export-csv?entity=${entity}`, '_blank');
  };

  if (loading && !summary) return <LoadingState text="Carregando central de TI..." />;

  const staffTabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Visão geral', icon: <Activity size={18} /> },
    { key: 'tickets', label: 'Chamados', icon: <MessageSquare size={18} /> },
    { key: 'assets', label: 'Ativos', icon: <Laptop size={18} /> },
    { key: 'access_credentials', label: 'Acessos', icon: <ShieldCheck size={18} /> },
    { key: 'access_matrix', label: 'Matriz de Acessos', icon: <Database size={18} /> },
    { key: 'certificates_licenses', label: 'Certificados', icon: <FileKey size={18} /> },
    { key: 'network_nas', label: 'Rede / NAS', icon: <Network size={18} /> },
    { key: 'maintenance', label: 'Manutenções', icon: <Wrench size={18} /> },
    { key: 'notes', label: 'Notas', icon: <StickyNote size={18} /> },
    { key: 'reports', label: 'Relatórios', icon: <BarChart3 size={18} /> },
    { key: 'settings', label: 'Configurações', icon: <Settings size={18} /> },
  ];

  return (
    <div className="it-page module-page">
      <ModuleHero
        accent="sky"
        icon={<Laptop size={28} />}
        title={isStaff ? "Gestão de TI" : "Central de Suporte (TI)"}
        description={isStaff ? "Operações de Tecnologia da Informação — chamados, ativos, cofre, certificados e relatórios." : "Abra chamados, acompanhe suas solicitações ou acerte seus acessos corporativos."}
        kodaMessage={isStaff ? "Operações em ordem! Precisa de ajuda com a governança da infraestrutura?" : "Olá! Precisa de suporte técnico? Abra um novo chamado e eu ajudo a acompanhar!"}
        compact={true}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={load} leftIcon={<RefreshCw size={16} />}>
              Atualizar
            </Button>
            <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)} leftIcon={<Plus size={16} />}>
              Novo chamado
            </Button>
          </>
        }
      />

      {isStaff && (
        <div className="it-tabs-glass" role="tablist">
          {staffTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              className={`it-tab-btn ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* FEEDBACK BANNERS */}
      {message && (
        <div className="glass-card" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: 'rgba(52, 211, 153, 0.35)' }}>
          <span style={{ color: '#a7f3d0', fontWeight: 600 }}>{message}</span>
          <button type="button" onClick={() => setMessage('')} aria-label="Fechar"><X size={18} /></button>
        </div>
      )}
      {error && (
        <div className="glass-card" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: 'rgba(248, 113, 113, 0.35)' }}>
          <span style={{ color: '#fecaca', fontWeight: 600 }}>{error}</span>
          <button type="button" onClick={() => setError('')} aria-label="Fechar"><X size={18} /></button>
        </div>
      )}

      {!isStaff && (
        <div className="it-user-workspace grid grid-cols-1 md:grid-cols-3 gap-6" style={{ marginTop: '20px' }}>
          <div className="space-y-6 md:col-span-1">
            <Card className="p-5 flex flex-col gap-4 bg-slate-900/35 border border-white/5 text-left">
              <h3 className="text-lg font-bold text-white">Autoatendimento</h3>
              <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                Precisa de ajuda ou algum recurso de TI? Abra um chamado de suporte e nossa equipe resolverá.
              </p>
              <Button variant="primary" size="md" onClick={() => setCreateOpen(true)} leftIcon={<Plus size={16} />} className="w-full">
                Abrir Novo Chamado
              </Button>
            </Card>

            <Card className="p-5 flex flex-col gap-4 bg-slate-900/35 border border-white/5 text-left">
              <h3 className="text-lg font-bold text-white">Meu Computador</h3>
              <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                Compartilhe as especificações deste dispositivo com o suporte técnico para facilitar o diagnóstico de problemas.
              </p>
              {collectedSpecs ? (
                <div className="bg-slate-950/45 p-3 rounded-xl border border-white/5 space-y-2 text-xs text-left font-bold text-slate-350">
                  <div><span className="text-slate-500 font-bold block uppercase text-[10px]">Hostname</span> <span className="text-white font-bold">{collectedSpecs.hostname}</span></div>
                  <div><span className="text-slate-500 font-bold block uppercase text-[10px]">Processador</span> <span className="text-white font-bold">{collectedSpecs.processor}</span></div>
                  <div><span className="text-slate-500 font-bold block uppercase text-[10px]">RAM</span> <span className="text-white font-bold">{collectedSpecs.ram_total || collectedSpecs.ram}</span></div>
                  <div><span className="text-slate-500 font-bold block uppercase text-[10px]">Sistema</span> <span className="text-white font-bold">{collectedSpecs.os}</span></div>
                  <Button variant="secondary" size="sm" onClick={handleCollectLocal} disabled={collectLoading} className="w-full mt-2">
                    {collectLoading ? 'Lendo...' : 'Recoletar Dados'}
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Button variant="secondary" size="sm" onClick={handleCollectLocal} disabled={collectLoading} className="w-full" leftIcon={<Laptop size={14} />}>
                    {collectLoading ? 'Lendo Especificações...' : 'Coletar dados do computador'}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => {
                    navigator.clipboard.writeText(POWERSHELL_COLLECT_SCRIPT);
                    setMessage("Script copiado! Execute no PowerShell e nos envie o resultado.");
                  }} className="w-full text-xs font-bold text-slate-300">
                    Copiar script manual
                  </Button>
                  <details className="mt-2 text-left bg-slate-950/40 p-2 rounded border border-white/5">
                    <summary className="text-xs text-slate-400 cursor-pointer font-bold hover:text-white transition-colors">
                      Ver Script PowerShell
                    </summary>
                    <pre className="text-[10px] text-slate-300 font-mono mt-2 overflow-x-auto p-2 bg-black/35 rounded max-h-48 whitespace-pre-wrap select-all">
                      {POWERSHELL_COLLECT_SCRIPT}
                    </pre>
                  </details>
                </div>
              )}
            </Card>
          </div>

          <div className="md:col-span-2 space-y-4 text-left">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-white">Meus chamados ativos</h3>
              <span className="text-xs text-slate-400 font-bold">{tickets.length} chamados registrados</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {tickets.map((ticket) => {
                const isUrgent = ticket.priority === 'CRITICA' || ticket.priority === 'ALTA';
                return (
                  <Card
                    key={ticket.id}
                    variant="interactive"
                    className={`ticket-product-card ${isUrgent ? 'ticket-product-card--urgent' : ''}`}
                  >
                    <div className="space-y-2">
                      <div className="flex justify-between items-start gap-2">
                        <Badge className="ticket-number-chip">{ticket.ticket_number}</Badge>
                        <div className="flex gap-1.5">
                          <span className={`status-mini status-mini--${ticket.status.toLowerCase()}`}>
                            {statusLabel(ticket.status)}
                          </span>
                          <span className={`priority-mini priority-mini--${ticket.priority.toLowerCase()}`}>
                            {priorityLabel(ticket.priority)}
                          </span>
                        </div>
                      </div>
                      <h4 className="text-base font-bold text-white line-clamp-1">{ticket.title}</h4>
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{ticket.description}</p>
                    </div>

                    <div className="flex justify-between items-center pt-3 border-t border-white/5 text-[11px] font-bold text-slate-400 mt-4">
                      <span>{ticket.assignee_name ? `Suporte: ${ticket.assignee_name}` : 'Aguardando técnico'}</span>
                      <Button variant="secondary" size="sm" onClick={() => openTicket(ticket)}>
                        Detalhes
                      </Button>
                    </div>
                  </Card>
                );
              })}

              {tickets.length === 0 && (
                <div className="col-span-2 py-12">
                  <EmptyState
                    icon={<CheckCircle size={48} />}
                    title="Nenhum chamado ativo"
                    description="Tudo limpo por aqui! Você não possui nenhum chamado de suporte em aberto."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'overview' && isStaff && (
        <ITOverview
          summary={summary}
          pcsInUseCount={assetsList.filter(a => a.status === 'EM_USO').length}
          changeLogs={changeLogs}
          isTauri={isTauriApp()}
          collectLoading={collectLoading}
          onCollectLocal={handleCollectLocal}
          onJsonImport={() => setJsonImportOpen(true)}
          onCsvImport={() => setCsvImportOpen(true)}
          onNewCredential={() => {
            setGenericForm({ title: "", system_name: "", username: "", secret: "", visibility_level: "IT_MANAGER" });
            setGenericModalOpen('vault');
          }}
          onNewNote={() => {
            setGenericForm({ title: "", content: "", color: "yellow", tags: [] });
            setGenericModalOpen('note');
          }}
          onCopyScript={() => {
            navigator.clipboard.writeText(POWERSHELL_COLLECT_SCRIPT);
            setMessage("Script do PowerShell copiado para a área de transferência! Cole em um terminal PowerShell para gerar o JSON.");
          }}
        />
      )}

      {/* ==============================================================================
          ABA 2: CHAMADOS (UNIFICADO)
          ============================================================================== */}
      {activeTab === 'tickets' && isStaff && (
        <ITTickets
          tickets={tickets}
          isStaff={isStaff}
          currentUser={currentUser}
          queueFilters={queueFilters}
          onSetQueueFilters={setQueueFilters}
          onOpenTicket={openTicket}
          onCreateTicket={() => setCreateOpen(true)}
          emptyFilters={emptyFilters}
          statusOptions={statusOptions}
          priorityOptions={priorityOptions}
          categoryOptions={categoryOptions}
        />
      )}

      {/* ==============================================================================
          ABA 3: ATIVOS (INVENTÁRIO COM FICHA COMPLETA)
          ============================================================================== */}
      {activeTab === 'assets' && isStaff && (
        <ITAssets
          assetsList={assetsList}
          onOpenAssetDetail={handleOpenAssetDetail}
          onCollectLocal={handleCollectLocal}
          onCreateAsset={() => { setAssetForm({}); setAssetFormOpen(true); }}
          onCsvImport={() => setCsvImportOpen(true)}
          isTauri={isTauriApp()}
          collectLoading={collectLoading}
          activeAssetTypes={activeAssetTypes}
        />
      )}

      {/* ==============================================================================
          ABA 4: ACESSOS & COFRE
          ============================================================================== */}
      {activeTab === 'access_credentials' && isStaff && (
        <ITCredentials
          corporateEmails={corporateEmails}
          changeLogs={changeLogs}
          onNewVault={() => {
            setGenericForm({ title: "", system_name: "", username: "", secret: "", visibility_level: "IT_TECH" });
            setGenericModalOpen('vault');
          }}
          onEditVault={(cred: any) => {
            setGenericForm(cred);
            setGenericModalOpen('vault');
          }}
          onDeleteVault={(cred: any) => {
            handleDeleteRecord('/credentials', cred.id, 'Credencial', cred.title);
          }}
          onNewEmail={() => {
            setGenericForm({ email_address: "", login: "", status: "ATIVO" });
            setGenericModalOpen('email');
          }}
          onEditEmail={(email: any) => {
            setGenericForm(email);
            setGenericModalOpen('email');
          }}
          onDeleteEmail={(email: any) => {
            handleDeleteRecord('/corporate-emails', email.id, 'E-mail Corporativo', email.email_address);
          }}
          onNewAccess={() => {
            setGenericForm({ system_name: "", access_type: "", url: "", responsible_team: "" });
            setGenericModalOpen('accessCatalog');
          }}
        />
      )}

      {/* ==============================================================================
          ABA: MATRIZ DE ACESSOS DE TI
          ============================================================================== */}
      {activeTab === 'access_matrix' && isStaff && (
        <div style={{ marginTop: '16px' }}>
          <AdminRealDataDashboard onBack={() => setActiveTab('access_credentials')} />
        </div>
      )}

      {/* ==============================================================================
          ABA 5: CERTIFICADOS & LICENÇAS
          ============================================================================== */}
      {activeTab === 'certificates_licenses' && isStaff && (
        <ITCertificates
          certificates={certificates}
          onNew={() => {
            setGenericForm({ name: "", domain_or_system: "", issuer: "", provider: "", expires_at: new Date().toISOString().split('T')[0] });
            setGenericModalOpen('certificate');
          }}
          onEdit={(cert: any) => {
            setGenericForm(cert);
            setGenericModalOpen('certificate');
          }}
          onDelete={(cert: any) => {
            handleDeleteRecord('/certificates', cert.id, 'Certificado', cert.name);
          }}
          onReload={load}
          setMessage={setMessage}
        />
      )}

      {/* ==============================================================================
          ABA 6: REDE & NAS
          ============================================================================== */}
      {activeTab === 'network_nas' && isStaff && (
        <ITNetwork
          networkItems={networkItems}
          nasFolders={nasFolders}
          onNewNetwork={() => {
            setGenericForm({ name: "", item_type: "OUTRO", ip_address: "", location: "", status: "ATIVO" });
            setGenericModalOpen('network');
          }}
          onEditNetwork={(net: any) => {
            setGenericForm(net);
            setGenericModalOpen('network');
          }}
          onDeleteNetwork={(net: any) => {
            handleDeleteRecord('/network-items', net.id, 'Dispositivo de Rede', net.name);
          }}
          onNewNas={() => {
            setGenericForm({ name: "", network_path: "", drive_letter: "Z:", permission_level: "LEITURA" });
            setGenericModalOpen('nas');
          }}
          onEditNas={(nas: any) => {
            setGenericForm(nas);
            setGenericModalOpen('nas');
          }}
          onDeleteNas={(nas: any) => {
            handleDeleteRecord('/nas', nas.id, 'Pasta NAS', nas.name);
          }}
        />
      )}

      {/* ==============================================================================
          ABA 7: MANUTENÇÕES
          ============================================================================== */}
      {activeTab === 'maintenance' && isStaff && (
        <ITMaintenance
          maintenances={maintenances}
          assetsList={assetsList}
          onNew={() => {
            setGenericForm({ title: "", description: "", status: "AGENDADA", asset_id: null });
            setGenericModalOpen('maintenance');
          }}
          onEdit={(maint: any) => {
            setGenericForm(maint);
            setGenericModalOpen('maintenance');
          }}
          onDelete={(maint: any) => {
            handleDeleteRecord('/maintenance-records', maint.id, 'Registro de Manutenção', maint.title);
          }}
        />
      )}

      {/* ==============================================================================
          ABA 8: NOTAS / STICKY NOTES COLORIDAS
          ============================================================================== */}
      {activeTab === 'notes' && isStaff && (
        <ITNotes
          notes={notes}
          onNew={() => {
            setGenericForm({ title: "", content: "", color: "yellow", tags: [], is_pinned: false });
            setGenericModalOpen('note');
          }}
          onEdit={(note: any) => {
            setGenericForm(note);
            setGenericModalOpen('note');
          }}
          onArchive={handleArchiveNote}
          onDelete={(note: any) => {
            handleDeleteRecord('/notes', note.id, 'Nota', note.title);
          }}
        />
      )}

      {/* ==============================================================================
          ABA 9: RELATÓRIOS (EXPORTAÇÃO CSV)
          ============================================================================== */}
      {activeTab === 'reports' && isStaff && (
        <ITReports
          tickets={tickets}
          assetsList={assetsList}
          certificates={certificates}
          maintenances={maintenances}
          onExportCSV={handleExportCSV}
        />
      )}

      {/* ==============================================================================
          ABA 10: CONFIGURAÇÕES (SLA, CAMPOS PERSONALIZADOS)
          ============================================================================== */}
      {activeTab === 'settings' && isStaff && (
        <ITSettings
          customFields={customFields}
          customCategories={customCategories}
          customAssetTypes={customAssetTypes}
          onNewCustomField={() => {
            setGenericForm({ name: "", field_type: "TEXT", options: [], is_active: true });
            setGenericModalOpen('custom_field');
          }}
          onUpdateCategories={(categories) => {
            setCustomCategories(categories);
            localStorage.setItem('vesper.it.custom_categories', JSON.stringify(categories));
          }}
          onUpdateAssetTypes={(types) => {
            setCustomAssetTypes(types);
            localStorage.setItem('vesper.it.custom_asset_types', JSON.stringify(types));
          }}
        />
      )}

      {/* ==============================================================================
          MODAIS E DRAWERS DE DETALHE
          ============================================================================== */}

      {/* 1. Modal / Drawer Completo de Detalhe do Ativo */}
      {selectedAsset && (
        <Drawer
          open={!!selectedAsset}
          onClose={() => setSelectedAsset(null)}
          title={`Ficha: ${selectedAsset.hostname || selectedAsset.name}`}
          description={`${selectedAsset.asset_tag || "Sem patrimônio cadastrado"} · ${activeAssetTypes.find((type) => type.value === selectedAsset.asset_type)?.label || selectedAsset.asset_type || 'Tipo não informado'}`}
        >
          <div className="space-y-4">
            <div className="flex border-b border-slate-700/50 overflow-x-auto pb-1 mb-4 gap-1">
              {[
                { key: 'resumo', label: 'Resumo' },
                { key: 'hardware', label: 'Hardware' },
                { key: 'rede', label: 'Rede' },
                { key: 'perifericos', label: 'Periféricos' },
                { key: 'manutencoes', label: 'Manutenções' },
                { key: 'historico', label: 'Histórico' }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveAssetDetailTab(tab.key)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg border whitespace-nowrap transition-colors ${
                    activeAssetDetailTab === tab.key
                      ? 'bg-sky-600/20 border-sky-500/50 text-sky-400'
                      : 'bg-transparent border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeAssetDetailTab === 'resumo' && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Hostname</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.hostname || "Não informado"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Código de Patrimônio</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.asset_tag || "Não informado"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Número de Série</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.serial_number || "Não informado"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Status</span>
                    <span className="text-sm font-bold text-white">{assetStatusLabel(selectedAsset.status)}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Fabricante</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.manufacturer || "Não informado"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Modelo</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.model || "Não informado"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Usuário Vinculado</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.assigned_to?.username || "Sem usuário"}</span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Setor / Local</span>
                    <span className="text-sm font-bold text-white">{selectedAsset.sector || selectedAsset.location || "Não informado"}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Garantia Até</span>
                    <span className="text-sm font-bold text-white">
                      {selectedAsset.warranty_until ? new Date(selectedAsset.warranty_until).toLocaleDateString('pt-BR') : "Não informado"}
                    </span>
                  </div>
                  <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                    <span className="text-[10px] text-slate-500 block uppercase font-black">Data de Compra</span>
                    <span className="text-sm font-bold text-white">
                      {selectedAsset.purchase_date ? new Date(selectedAsset.purchase_date).toLocaleDateString('pt-BR') : "Não informado"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {activeAssetDetailTab === 'hardware' && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Processador</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.processor || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Memória RAM</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.ram || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Placa-Mãe</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.motherboard || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Placa de Vídeo (GPU)</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.gpu || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Armazenamento</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.storage || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Fonte</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.power_supply || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Gabinete</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.cabinet || "Não informado"}</span>
                </div>
              </div>
            )}

            {activeAssetDetailTab === 'rede' && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Endereço IP</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.ip_address || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Ponto de Rede</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.network_point || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Ramal</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.ramal || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Setor</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.sector || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Placa de Rede</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.network_card || "Não informado"}</span>
                </div>
              </div>
            )}

            {activeAssetDetailTab === 'perifericos' && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Monitor</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.monitor || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Teclado</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.keyboard || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Mouse</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.mouse || "Não informado"}</span>
                </div>
                <div className="bg-slate-950/40 p-3 rounded-xl border border-white/5 col-span-2">
                  <span className="text-[10px] text-slate-500 block uppercase font-black">Outros Periféricos</span>
                  <span className="text-sm font-bold text-white">{selectedAsset.peripherals || "Nenhum outro cadastrado"}</span>
                </div>
              </div>
            )}

            {activeAssetDetailTab === 'manutencoes' && (
              <div className="space-y-3">
                {maintenances.filter(m => m.asset_id === selectedAsset.id).map((m) => (
                  <div key={m.id} className="bg-slate-950/40 p-3 rounded-xl border border-white/5 space-y-1 text-xs text-left">
                    <div className="flex justify-between font-bold text-sky-400">
                      <span>{m.title}</span>
                      <span className="bg-slate-800 text-[10px] px-1.5 py-0.5 rounded">{maintenanceStatusLabel(m.status)}</span>
                    </div>
                    <p className="text-slate-300">{m.description || "Sem observações registradas."}</p>
                    <div className="text-[10px] text-slate-500 pt-1 flex justify-between">
                      <span>Agendada: {m.scheduled_at ? new Date(m.scheduled_at).toLocaleString('pt-BR') : "Não agendada"}</span>
                      {m.completed_at && <span>Concluída: {new Date(m.completed_at).toLocaleString('pt-BR')}</span>}
                    </div>
                  </div>
                ))}
                {maintenances.filter(m => m.asset_id === selectedAsset.id).length === 0 && (
                  <p className="text-center text-xs text-slate-500 py-6 font-bold">Nenhuma manutenção agendada ou executada para este ativo.</p>
                )}
              </div>
            )}

            {activeAssetDetailTab === 'historico' && (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {assetHistory.map((h, index) => (
                  <div key={index} className="bg-slate-950/40 p-3 rounded-xl border border-white/5 text-xs text-left">
                    <div className="flex justify-between font-bold text-slate-500 mb-1">
                      <span>{new Date(h.created_at).toLocaleString('pt-BR')}</span>
                      <span>Por: {h.user?.username || "Sistema"}</span>
                    </div>
                    <div className="text-slate-300">
                      {h.action || 'Atualização registrada'} · <span className="font-bold text-slate-200">{fieldLabel(h.field_name)}</span> alterado de <span className="line-through text-slate-500">{h.old_value || "vazio"}</span> para <span className="font-bold text-sky-400">{h.new_value || "vazio"}</span>
                    </div>
                  </div>
                ))}
                {assetHistory.length === 0 && (
                  <p className="text-center text-xs text-slate-500 py-6 font-bold">Nenhum evento registrado ainda.</p>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-700/40 mt-4 w-full">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setAssetForm(selectedAsset);
                setAssetFormOpen(true);
              }}
              className="flex-1 min-w-[120px] bg-slate-800 hover:bg-slate-700 text-white"
            >
              Editar Dados
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleRetireAsset(selectedAsset.id)}
              className="flex-1 min-w-[120px]"
            >
              Aposentar
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(POWERSHELL_COLLECT_SCRIPT);
                setMessage("Script de Coleta Manual copiado para a Área de Transferência!");
              }}
              className="flex-1 min-w-[120px] bg-slate-850 hover:bg-slate-800 text-slate-300"
            >
              Copiar Script Coleta
            </Button>
          </div>
        </Drawer>
      )}

      {/* 2. Modal de Cadastro/Edição de Ativo */}
      {assetFormOpen && (
        <Modal isOpen={true} onClose={() => setAssetFormOpen(false)} title={assetForm.id ? "Editar Equipamento" : "Novo Equipamento"} size="lg">
          <form onSubmit={handleSaveAsset} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Input label="Nome do Ativo" value={assetForm.name || ""} onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })} required />
              <Input label="Código de Patrimônio (Asset Tag)" value={assetForm.asset_tag || ""} onChange={(e) => setAssetForm({ ...assetForm, asset_tag: e.target.value })} />
              <Select
                label="Tipo de Ativo"
                value={assetForm.asset_type || "PC"}
                options={[
                  { value: 'PC', label: 'Computador/Desktop' },
                  { value: 'NOTEBOOK', label: 'Notebook' },
                  { value: 'MONITOR', label: 'Monitor' },
                  { value: 'IMPRESSORA', label: 'Impressora' },
                  { value: 'SERVIDOR', label: 'Servidor' },
                  { value: 'ROTEADOR', label: 'Roteador' },
                  { value: 'SWITCH', label: 'Switch' },
                  { value: 'OUTRO', label: 'Outro' }
                ]}
                onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}
              />
              <Select
                label="Status"
                value={assetForm.status || "DISPONIVEL"}
                options={[
                  { value: 'DISPONIVEL', label: 'Disponível' },
                  { value: 'EM_USO', label: 'Em Uso' },
                  { value: 'MANUTENCAO', label: 'Em Manutenção' },
                  { value: 'APOSENTADO', label: 'Aposentado/Arquivado' }
                ]}
                onChange={(e) => setAssetForm({ ...assetForm, status: e.target.value })}
              />
              <Input label="Fabricante" value={assetForm.manufacturer || ""} onChange={(e) => setAssetForm({ ...assetForm, manufacturer: e.target.value })} />
              <Input label="Modelo" value={assetForm.model || ""} onChange={(e) => setAssetForm({ ...assetForm, model: e.target.value })} />
              <Input label="Número de Série" value={assetForm.serial_number || ""} onChange={(e) => setAssetForm({ ...assetForm, serial_number: e.target.value })} />
              <Input label="Hostname" value={assetForm.hostname || ""} onChange={(e) => setAssetForm({ ...assetForm, hostname: e.target.value })} />
              
              <Input label="Processador" value={assetForm.processor || ""} onChange={(e) => setAssetForm({ ...assetForm, processor: e.target.value })} />
              <Input label="Memória RAM" value={assetForm.ram || ""} onChange={(e) => setAssetForm({ ...assetForm, ram: e.target.value })} />
              <Input label="Placa-Mãe" value={assetForm.motherboard || ""} onChange={(e) => setAssetForm({ ...assetForm, motherboard: e.target.value })} />
              <Input label="GPU (Vídeo)" value={assetForm.gpu || ""} onChange={(e) => setAssetForm({ ...assetForm, gpu: e.target.value })} />
              <Input label="Armazenamento" value={assetForm.storage || ""} onChange={(e) => setAssetForm({ ...assetForm, storage: e.target.value })} />
              <Input label="Endereço IP" value={assetForm.ip_address || ""} onChange={(e) => setAssetForm({ ...assetForm, ip_address: e.target.value })} />
              
              <Input label="Ramal" value={assetForm.ramal || ""} onChange={(e) => setAssetForm({ ...assetForm, ramal: e.target.value })} />
              <Input label="Ponto de Rede" value={assetForm.network_point || ""} onChange={(e) => setAssetForm({ ...assetForm, network_point: e.target.value })} />
              <Input label="Setor" value={assetForm.sector || ""} onChange={(e) => setAssetForm({ ...assetForm, sector: e.target.value })} />
              <Input label="Responsável TI" value={assetForm.it_responsible || ""} onChange={(e) => setAssetForm({ ...assetForm, it_responsible: e.target.value })} />
            </div>
            <Textarea label="Observações Gerais" value={assetForm.notes || ""} onChange={(e) => setAssetForm({ ...assetForm, notes: e.target.value })} rows={3} />
            
            <div className="flex justify-end gap-2 pt-4">
              <button type="button" className="cartoon-btn" onClick={() => setAssetFormOpen(false)}>Cancelar</button>
              <button type="submit" className="cartoon-btn cartoon-btn-green">Salvar Ativo</button>
            </div>
          </form>
        </Modal>
      )}

      {/* 3. Modal de Importação JSON de Specs (Fallback Manual) */}
      {jsonImportOpen && (
        <Modal isOpen={true} onClose={() => setJsonImportOpen(false)} title="Importar Especificações de Coleta Manual" size="md">
          <div className="space-y-4">
            <p className="text-sm font-bold text-slate-700">Cole o conteúdo JSON gerado pelo script manual do computador local:</p>
            <Textarea
              placeholder='{"hostname": "VESPER-PC", "processor": "Intel...", ...}'
              value={manualJsonText}
              onChange={(e) => setManualJsonText(e.target.value)}
              rows={8}
            />
            <div className="flex justify-end gap-2">
              <button className="cartoon-btn" onClick={() => setJsonImportOpen(false)}>Cancelar</button>
              <button className="cartoon-btn cartoon-btn-primary" onClick={handleJsonImport}>Processar JSON</button>
            </div>
          </div>
        </Modal>
      )}

      {/* 4. Modal de Preview de Coleta de PC (Tauri / JSON) */}
      {collectModalOpen && previewDiff && (
        <Modal isOpen={true} onClose={() => setCollectModalOpen(false)} title="Diferenças Detectadas no Computador" size="lg">
          <div className="space-y-4">
            <div className="cartoon-card cartoon-bg-yellow p-4">
              <strong className="block text-sm">Origem dos Dados: Coleta Automática de PC</strong>
              {previewDiff.asset_found ? (
                <span className="text-xs text-slate-800 font-extrabold">🔗 Ativo existente correspondente encontrado: <span className="underline">{previewDiff.asset.name} (Tag: {previewDiff.asset.asset_tag || "sem tag"})</span></span>
              ) : (
                <span className="text-xs text-red-800 font-extrabold">🆕 Nenhum ativo correspondente encontrado por hostname/serial. Um novo ativo será criado.</span>
              )}
            </div>

            <h4 className="font-black text-md">Selecione as especificações locais a serem salvas no ativo:</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {previewDiff.diffs.map((diff: any) => (
                <label key={diff.field} className="p-3 rounded-lg border-2 border-black flex items-center justify-between hover:bg-slate-50 cursor-pointer text-sm font-semibold">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selectedFieldsToApply.includes(diff.field)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedFieldsToApply([...selectedFieldsToApply, diff.field]);
                        } else {
                          setSelectedFieldsToApply(selectedFieldsToApply.filter(f => f !== diff.field));
                        }
                      }}
                    />
                    <div>
                      <span className="font-extrabold block text-xs uppercase text-slate-500 flex items-center gap-2">
                        {diff.label}
                        {['ram', 'storage', 'processor', 'ip_address', 'mac_address'].includes(diff.field) && (
                          <span className="px-1.5 py-0.5 text-[9px] font-black bg-amber-100 text-amber-800 border border-amber-800 rounded">
                            Divergência Crítica
                          </span>
                        )}
                      </span>
                      <span>Atual: <span className="line-through">{diff.current || "não informado"}</span> ➔ <span className="text-green-700 font-bold">{diff.collected}</span></span>
                    </div>
                  </div>
                </label>
              ))}
              {previewDiff.diffs.length === 0 && (
                <p className="text-center py-6 text-slate-600 font-bold bg-slate-100 rounded-lg">
                  ✅ Todas as especificações já estão idênticas ao banco de dados do ativo!
                </p>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <button className="cartoon-btn" onClick={() => setCollectModalOpen(false)}>Cancelar</button>
              <button className="cartoon-btn cartoon-btn-green" onClick={handleConfirmSpecs}>Aplicar e Salvar</button>
            </div>
          </div>
        </Modal>
      )}

      {/* 5. Modal de Importação CSV/XLSX */}
      {csvImportOpen && (
        <Modal isOpen={true} onClose={() => setCsvImportOpen(false)} title="Importação de Ativos por CSV" size="lg">
          <div className="space-y-4">
            <p className="text-xs font-bold text-slate-600">
              Digite as linhas do CSV abaixo. A primeira linha deve conter as colunas exatamente como: <br />
              <code className="bg-slate-100 p-1 border border-black rounded font-mono">name,asset_tag,asset_type,serial_number,hostname,manufacturer,model</code>
            </p>
            <Textarea
              placeholder="name,asset_tag,asset_type,serial_number&#10;PC Recepcao,VESP-0012,PC,SN12345&#10;Notebook TI,VESP-0013,NOTEBOOK,SN67890"
              value={csvContent}
              onChange={(e) => setCsvContent(e.target.value)}
              rows={8}
            />
            <div className="flex justify-between items-center">
              <label className="flex items-center gap-2 font-bold text-xs">
                <input type="checkbox" checked={csvUpdateExisting} onChange={(e) => setCsvUpdateExisting(e.target.checked)} />
                Atualizar ativos existentes com mesma tag/serial
              </label>
              <button className="cartoon-btn cartoon-btn-blue py-1 px-3 text-xs" onClick={handleCSVPreview}>
                Visualizar Preview
              </button>
            </div>

            {csvPreview.length > 0 && (
              <div className="space-y-2 border-2 border-black rounded-lg p-3 bg-slate-50 max-h-48 overflow-y-auto">
                <strong className="text-xs block mb-2">Linhas a serem importadas ({csvPreview.length}):</strong>
                <table className="w-full text-xs font-bold text-left border-collapse">
                  <thead>
                    <tr className="border-b border-black">
                      <th className="p-1">Nome</th>
                      <th className="p-1">Tag</th>
                      <th className="p-1">Tipo</th>
                      <th className="p-1">Serial</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreview.map((p, index) => (
                      <tr key={index} className="border-b border-slate-200">
                        <td className="p-1">{p.name}</td>
                        <td className="p-1">{p.asset_tag}</td>
                        <td className="p-1">{p.asset_type}</td>
                        <td className="p-1">{p.serial_number}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <button className="cartoon-btn" onClick={() => setCsvImportOpen(false)}>Cancelar</button>
              <button className="cartoon-btn cartoon-btn-green" onClick={handleCSVConfirm} disabled={csvPreview.length === 0}>
                Confirmar Importação Real
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* 6. Modais de criação de outras entidades genéricas */}
      {genericModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setGenericModalOpen(null)}
          title={
            genericModalOpen === 'email' ? 'Configurar E-mail Corporativo' :
            genericModalOpen === 'nas' ? 'Mapeamento de Diretório NAS' :
            (genericModalOpen === 'vault' || genericModalOpen === 'credentials') ? 'Credencial segura do cofre' :
            genericModalOpen === 'note' ? 'Lembrete Técnico (Post-it)' :
            genericModalOpen === 'custom_field' ? 'Campo Personalizado de Ativo' :
            genericModalOpen === 'certificate' ? 'Certificado SSL ou Licença' :
            genericModalOpen === 'network' ? 'Equipamento de Rede' :
            genericModalOpen === 'maintenance' ? 'Ordem de Manutenção' :
            genericModalOpen === 'accessCatalog' ? 'Catalogar Novo Sistema/Acesso' :
            `Gerenciar ${genericModalOpen}`
          }
          size="md"
        >
          <div className="space-y-4">
            {genericModalOpen === 'email' && (
              <div className="space-y-3">
                <Input label="Endereço de E-mail" value={genericForm.email_address || ""} onChange={(e) => setGenericForm({ ...genericForm, email_address: e.target.value })} required />
                <Input label="Login" value={genericForm.login || ""} onChange={(e) => setGenericForm({ ...genericForm, login: e.target.value })} />
                <Input label="Configurações de Servidor" value={genericForm.server_config || ""} onChange={(e) => setGenericForm({ ...genericForm, server_config: e.target.value })} />
                <Input label="Cliente Recomendado (ex: Thunderbird)" value={genericForm.recommended_client || ""} onChange={(e) => setGenericForm({ ...genericForm, recommended_client: e.target.value })} />
                <Select
                  label="Vincular Credencial do Cofre"
                  value={genericForm.credential_id || ""}
                  options={[
                    { value: "", label: "Nenhuma credencial vinculada" },
                    ...changeLogs.filter(c => c.entity_type === 'Credential').map(c => ({ value: String(c.entity_id), label: `Credencial #${c.entity_id}` }))
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, credential_id: e.target.value ? Number(e.target.value) : null })}
                />
              </div>
            )}

            {(genericModalOpen === 'vault' || genericModalOpen === 'credentials') && (
              <div className="space-y-3">
                <Input label="Título da credencial" value={genericForm.title || ""} onChange={(e) => setGenericForm({ ...genericForm, title: e.target.value })} required />
                <Input label="Sistema ou recurso" value={genericForm.system_name || ""} onChange={(e) => setGenericForm({ ...genericForm, system_name: e.target.value })} required />
                <Input label="Usuário / Login" value={genericForm.username || ""} onChange={(e) => setGenericForm({ ...genericForm, username: e.target.value })} />
                <Input label={genericForm.id ? "Nova senha ou segredo (opcional)" : "Senha ou segredo"} type="password" value={genericForm.secret || ""} onChange={(e) => setGenericForm({ ...genericForm, secret: e.target.value })} required={!genericForm.id} />
                <Input label="URL de acesso" value={genericForm.url || ""} onChange={(e) => setGenericForm({ ...genericForm, url: e.target.value })} />
                <Select
                  label="Quem pode acessar"
                  value={genericForm.visibility_level || "IT_TECH"}
                  options={[
                    { value: "IT_TECH", label: "Técnicos de TI" },
                    { value: "IT_ADMIN", label: "Administradores de TI" }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, visibility_level: e.target.value })}
                />
                <Textarea label="Observações seguras" value={genericForm.notes || ""} onChange={(e) => setGenericForm({ ...genericForm, notes: e.target.value })} rows={3} />
                <p className="text-xs text-slate-400 font-semibold">
                  O segredo não aparece em listas. Revelar ou copiar exige confirmação e gera auditoria.
                </p>
              </div>
            )}

            {genericModalOpen === 'accessCatalog' && (
              <div className="space-y-3">
                <Input label="Nome do Sistema" value={genericForm.system_name || ""} onChange={(e) => setGenericForm({ ...genericForm, system_name: e.target.value })} required />
                <Input label="Tipo de Acesso (ex: Web, VPN, SSH)" value={genericForm.access_type || ""} onChange={(e) => setGenericForm({ ...genericForm, access_type: e.target.value })} required />
                <Input label="URL de Acesso" value={genericForm.url || ""} onChange={(e) => setGenericForm({ ...genericForm, url: e.target.value })} />
                <Input label="Equipe Responsável" value={genericForm.responsible_team || ""} onChange={(e) => setGenericForm({ ...genericForm, responsible_team: e.target.value })} />
              </div>
            )}

            {genericModalOpen === 'nas' && (
              <div className="space-y-3">
                <Input label="Nome do Mapeamento / Pasta" value={genericForm.name || ""} onChange={(e) => setGenericForm({ ...genericForm, name: e.target.value })} required />
                <Input label="Caminho de Rede (ex: \\QNAP-NAS\arquivos)" value={genericForm.network_path || ""} onChange={(e) => setGenericForm({ ...genericForm, network_path: e.target.value })} />
                <Input label="Letra Recomendada (ex: Z:)" value={genericForm.drive_letter || ""} onChange={(e) => setGenericForm({ ...genericForm, drive_letter: e.target.value })} />
                <Select
                  label="Permissão Recomendada"
                  value={genericForm.permission_level || "LEITURA"}
                  options={[
                    { value: "LEITURA", label: "Apenas Leitura" },
                    { value: "ESCRITA", label: "Leitura e Escrita" },
                    { value: "ADMIN", label: "Administrador da Pasta" }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, permission_level: e.target.value })}
                />
              </div>
            )}

            {genericModalOpen === 'note' && (
              <div className="space-y-3">
                <Input label="Título da Nota" value={genericForm.title || ""} onChange={(e) => setGenericForm({ ...genericForm, title: e.target.value })} />
                <Textarea label="Conteúdo do Lembrete" value={genericForm.content || ""} onChange={(e) => setGenericForm({ ...genericForm, content: e.target.value })} rows={4} required />
                <Select
                  label="Cor do Post-it"
                  value={genericForm.color || "yellow"}
                  options={[
                    { value: 'yellow', label: 'Amarelo' },
                    { value: 'blue', label: 'Azul' },
                    { value: 'green', label: 'Verde' },
                    { value: 'pink', label: 'Rosa' },
                    { value: 'orange', label: 'Laranja' },
                    { value: 'purple', label: 'Roxo' }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, color: e.target.value })}
                />
              </div>
            )}

            {genericModalOpen === 'custom_field' && (
              <div className="space-y-3">
                <Input label="Nome do Campo Adicional" value={genericForm.name || ""} onChange={(e) => setGenericForm({ ...genericForm, name: e.target.value })} required />
                <Select
                  label="Tipo do Campo"
                  value={genericForm.field_type || "TEXT"}
                  options={[
                    { value: "TEXT", label: "Texto Livre" },
                    { value: "NUMBER", label: "Número" },
                    { value: "DATE", label: "Data" },
                    { value: "BOOLEAN", label: "Sim/Não" }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, field_type: e.target.value })}
                />
              </div>
            )}

            {genericModalOpen === 'certificate' && (
              <div className="space-y-3">
                <Input label="Nome do Certificado / Licença" value={genericForm.name || ""} onChange={(e) => setGenericForm({ ...genericForm, name: e.target.value })} required />
                <Input label="Domínio / Sistema correspondente" value={genericForm.domain_or_system || ""} onChange={(e) => setGenericForm({ ...genericForm, domain_or_system: e.target.value })} required />
                <Input label="Emissor" value={genericForm.issuer || ""} onChange={(e) => setGenericForm({ ...genericForm, issuer: e.target.value })} />
                <Input label="Fornecedor / Revendedor" value={genericForm.provider || ""} onChange={(e) => setGenericForm({ ...genericForm, provider: e.target.value })} />
                <Input label="Vencimento" type="date" value={genericForm.expires_at ? genericForm.expires_at.split('T')[0] : ""} onChange={(e) => setGenericForm({ ...genericForm, expires_at: e.target.value })} required />
              </div>
            )}

            {genericModalOpen === 'network' && (
              <div className="space-y-3">
                <Input label="Nome do Equipamento" value={genericForm.name || ""} onChange={(e) => setGenericForm({ ...genericForm, name: e.target.value })} required />
                <Select
                  label="Tipo de Item de Rede"
                  value={genericForm.item_type || "ROTEADOR"}
                  options={[
                    { value: "ROTEADOR", label: "Roteador" },
                    { value: "SWITCH", label: "Switch" },
                    { value: "ACCESS_POINT", label: "Access Point" },
                    { value: "LINK", label: "Link de Internet" },
                    { value: "FIREWALL", label: "Firewall" },
                    { value: "OUTRO", label: "Outro" }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, item_type: e.target.value })}
                />
                <Input label="Endereço IP" value={genericForm.ip_address || ""} onChange={(e) => setGenericForm({ ...genericForm, ip_address: e.target.value })} />
                <Input label="Local Físico" value={genericForm.location || ""} onChange={(e) => setGenericForm({ ...genericForm, location: e.target.value })} />
              </div>
            )}

            {genericModalOpen === 'maintenance' && (
              <div className="space-y-3">
                <Input label="Título do Reparo / Manutenção" value={genericForm.title || ""} onChange={(e) => setGenericForm({ ...genericForm, title: e.target.value })} required />
                <Textarea label="Descrição Técnica" value={genericForm.description || ""} onChange={(e) => setGenericForm({ ...genericForm, description: e.target.value })} rows={3} />
                <Select
                  label="Status"
                  value={genericForm.status || "AGENDADA"}
                  options={[
                    { value: "AGENDADA", label: "Agendada" },
                    { value: "EM_ANDAMENTO", label: "Em Andamento" },
                    { value: "CONCLUIDA", label: "Concluída" },
                    { value: "CANCELADA", label: "Cancelada" }
                  ]}
                  onChange={(e) => setGenericForm({ ...genericForm, status: e.target.value })}
                />
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <button className="cartoon-btn" onClick={() => setGenericModalOpen(null)}>Cancelar</button>
              <button className="cartoon-btn cartoon-btn-green" onClick={handleGenericSave}>Confirmar</button>
            </div>
          </div>
        </Modal>
      )}

      {/* Reusar o modal de novo chamado original */}
      <CreateTicketModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(ticket) => {
          setMessage(`Chamado ${ticket.ticket_number} aberto com sucesso.`);
          load();
          openTicket(ticket);
        }}
      />

      {/* Detalhe do chamado com visual restrito e público */}
      {selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          isStaff={isStaff}
          onClose={() => setSelectedTicket(null)}
          onRefresh={refreshTicket}
          onMessage={setMessage}
        />
      )}



      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm(prev => ({ ...prev, isOpen: false }))}
        onConfirm={async () => {
          setDeleteConfirm(prev => ({ ...prev, isOpen: false }));
          await deleteConfirm.onConfirm();
        }}
        title={deleteConfirm.title}
        message={deleteConfirm.message}
        confirmText="Confirmar Exclusão"
        cancelText="Cancelar"
        variant="danger"
      />

      <ConfirmDialog
        isOpen={assetToRetire !== null}
        onClose={() => setAssetToRetire(null)}
        onConfirm={async () => {
          if (assetToRetire !== null) {
            const id = assetToRetire;
            setAssetToRetire(null);
            await confirmRetireAsset(id);
          }
        }}
        title="Aposentar Equipamento"
        message="Deseja aposentar/arquivar este equipamento? Esta ação não pode ser desfeita na operação e gerará auditoria ISO."
        confirmText="Confirmar Aposentadoria"
        cancelText="Cancelar"
        variant="danger"
      />
    </div>
  );
};

const TicketDetailModal: React.FC<{
  ticket: ITTicket;
  isStaff: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onMessage: (message: string) => void;
}> = ({ ticket, isStaff, onClose, onRefresh, onMessage }) => {
  const [comment, setComment] = useState('');
  const [internal, setInternal] = useState(false);
  const [saving, setSaving] = useState(false);

  const postComment = async () => {
    if (!comment.trim()) return;
    setSaving(true);
    try {
      await itRequest(`/tickets/${ticket.id}/comments`, {
        method: 'POST',
        body: JSON.stringify({ comment, is_internal: internal }),
      });
      setComment('');
      setInternal(false);
      onRefresh();
    } catch (err: any) {
      onMessage(err.message || 'Erro ao enviar comentário.');
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (statusValue: string) => {
    try {
      await itRequest(`/tickets/${ticket.id}/status`, {
        method: 'POST',
        body: JSON.stringify({
          status: statusValue,
          suspension_reason: statusValue === 'SUSPENSO' ? 'AGUARDANDO_USUARIO' : undefined,
        }),
      });
      onRefresh();
    } catch (err: any) {
      onMessage(err.message || 'Erro ao atualizar status.');
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title={`${ticket.ticket_number} - ${ticket.title}`} size="lg">
      <div className="it-ticket-detail" style={{ display: 'grid', gap: 20 }}>
        <div className="it-detail-summary" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <Badge>{statusLabel(ticket.status)}</Badge>
          {isStaff && <Badge>{priorityLabel(ticket.priority)}</Badge>}
          <span style={{ fontSize: 13, color: '#94a3b8' }}>
            Categoria: {categoryLabel(ticket.category)}
          </span>
          {isStaff && <span style={{ fontSize: 13, color: '#94a3b8' }}>SLA: {ticket.sla?.state || 'sem SLA'}</span>}
        </div>
        <p className="it-ticket-description" style={{ color: '#cbd5e1', fontSize: 14, lineHeight: 1.6, background: 'rgba(255,255,255,0.02)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.04)', margin: 0 }}>
          {ticket.description}
        </p>

        {isStaff && (
          <div className="it-staff-actions" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)', alignItems: 'end' }}>
            <div style={{ flex: 1, minWidth: 150 }}>
              <Select
                label="Atualizar Status"
                value={ticket.status}
                options={statusOptions}
                onChange={(event) => setStatus(event.target.value)}
              />
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => itRequest(`/tickets/${ticket.id}/assign`, { method: 'POST', body: JSON.stringify({}) }).then(onRefresh).catch((err) => onMessage(err.message))}
              leftIcon={<Play size={14} />}
            >
              Assumir
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => itRequest(`/tickets/${ticket.id}/time/start`, { method: 'POST' }).then(onRefresh).catch((err) => onMessage(err.message))}
              leftIcon={<Clock size={14} />}
            >
              Iniciar tempo
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => itRequest(`/tickets/${ticket.id}/create-kanban-card`, { method: 'POST', body: JSON.stringify({}) }).then(() => { onMessage('Card Kanban criado ou já vinculado.'); onRefresh(); }).catch((err) => onMessage(err.message))}
              leftIcon={<Kanban size={14} />}
            >
              {ticket.kanban_card_id ? 'Card vinculado' : 'Criar Kanban'}
            </Button>
          </div>
        )}

        <section style={{ display: 'grid', gap: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', margin: '10px 0 0 0', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 6 }}>Comentários</h3>
          <div className="it-comments" style={{ display: 'grid', gap: 10, maxHeight: 180, overflowY: 'auto', paddingRight: 6 }}>
            {(ticket.comments || []).map((item) => (
              <div key={item.id} className={`it-comment ${item.is_internal ? 'internal' : ''}`} style={{ background: item.is_internal ? 'rgba(234,179,8,0.04)' : 'rgba(255,255,255,0.02)', border: item.is_internal ? '1px solid rgba(234,179,8,0.15)' : '1px solid rgba(255,255,255,0.04)', padding: 10, borderRadius: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, alignItems: 'center' }}>
                  <strong style={{ color: '#fff', fontSize: 12 }}>{item.author_name || 'Usuário'}</strong>
                  {item.is_internal && <Badge variant="warning" style={{ fontSize: 9, padding: '2px 4px' }}>Interno</Badge>}
                </div>
                <p style={{ margin: 0, color: '#cbd5e1', fontSize: 13, lineHeight: 1.4 }}>{item.comment}</p>
              </div>
            ))}
            {(ticket.comments || []).length === 0 && <span style={{ color: '#64748b', fontSize: 12 }}>Nenhum comentário registrado.</span>}
          </div>
          
          <div style={{ display: 'grid', gap: 8, marginTop: 4 }}>
            <Textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Escreva uma atualização ou nota..."
              rows={3}
              style={{ marginBottom: 0 }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
              {isStaff ? (
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8', cursor: 'pointer' }}>
                  <input type="checkbox" checked={internal} onChange={(event) => setInternal(event.target.checked)} style={{ accentColor: 'var(--primary-color)' }} />
                  <span>Comentário interno (apenas equipe de TI)</span>
                </label>
              ) : <div />}
              <Button onClick={postComment} isLoading={saving} disabled={!comment.trim()} leftIcon={<Send size={14} />}>
                Enviar
              </Button>
            </div>
          </div>
        </section>

        {isStaff && (ticket.checklists || []).length > 0 && (
          <section style={{ display: 'grid', gap: 10 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', margin: 0, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 6 }}>Checklist técnico</h3>
            <div style={{ display: 'grid', gap: 8 }}>
              {(ticket.checklists || []).map((checklist) => (
                <div key={checklist.id} style={{ background: 'rgba(255,255,255,0.02)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.04)' }}>
                  <strong style={{ display: 'block', fontSize: 12, color: '#fff', marginBottom: 6 }}>{checklist.title}</strong>
                  <div style={{ display: 'grid', gap: 4 }}>
                    {(checklist.items || []).map((item) => (
                      <span key={item.id} style={{ fontSize: 12, color: item.is_done ? '#34d399' : '#94a3b8', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>{item.is_done ? '✓' : '○'}</span>
                        <span style={{ textDecoration: item.is_done ? 'line-through' : 'none' }}>{item.text}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section style={{ display: 'grid', gap: 10 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', margin: 0, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 6 }}>Anexos</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(ticket.attachments || []).map((attachment) => (
              <a
                key={attachment.id}
                href={`/api/v1/it/ticket-attachments/${attachment.id}/download`}
                target="_blank"
                rel="noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 6, fontSize: 12, color: '#38bdf8', textDecoration: 'none' }}
              >
                <Paperclip size={12} />
                <span>{attachment.filename || `Anexo ${attachment.id}`}</span>
              </a>
            ))}
            {(ticket.attachments || []).length === 0 && <span style={{ color: '#64748b', fontSize: 12 }}>Nenhum anexo disponível.</span>}
          </div>
        </section>
      </div>
    </Modal>
  );
};

export default ITPage;
