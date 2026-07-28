import React, { useState, useEffect, useMemo } from 'react';

import { Lock, Mail, Server, Plus, Key, Eye, EyeOff, Copy, CheckCircle2, Shield, Calendar, User, ArrowRight, ExternalLink, HelpCircle, Download, Search } from 'lucide-react';

import { Card } from '../ui/Card';

import { Button } from '../ui/Button';

import { Badge } from '../ui/Badge';

import { KodaMascot } from '../ui/KodaMascot';

import { Drawer } from '../ui/Drawer';

import { Input } from '../ui/Input';

import { itRequest } from './itApi';

import { ConfirmDialog } from '../ui/ConfirmDialog';



export interface ITCredentialsProps {

  corporateEmails: any[];

  changeLogs?: any[];

  onNewVault: () => void;

  onEditVault: (cred: any) => void;

  onNewEmail: () => void;

  onEditEmail: (email: any) => void;

  onNewAccess: () => void;

  onDeleteEmail: (email: any) => void;

  onDeleteVault: (cred: any) => void;

}



export const ITCredentials: React.FC<ITCredentialsProps> = ({

  corporateEmails,

  changeLogs = [],

  onNewVault,

  onEditVault,

  onNewEmail,

  onEditEmail,

  onNewAccess,

  onDeleteEmail,

  onDeleteVault,

}) => {

  const [credentials, setCredentials] = useState<any[]>([]);

  const [selectedCred, setSelectedCred] = useState<any | null>(null);

  const [revealed, setRevealed] = useState<string | null>(null);

  const [copySuccess, setCopySuccess] = useState(false);

  const [confirmRevealId, setConfirmRevealId] = useState<number | null>(null);

  const [confirmCopyId, setConfirmCopyId] = useState<number | null>(null);

  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const [catalogSearch, setCatalogSearch] = useState('');

  const [catalogTypeFilter, setCatalogTypeFilter] = useState('');



  const loadCredentials = async () => {

    try {

      const creds = await itRequest<any[]>('/credentials');

      setCredentials(creds);

    } catch {}

  };



  const handleDeleteAfterConfirm = async () => {

    if (confirmDeleteId === null) return;

    const id = confirmDeleteId;

    setConfirmDeleteId(null);

    try {

      await itRequest(`/credentials/${id}`, { method: 'DELETE' });

      setSelectedCred(null);

      setRevealed(null);

      loadCredentials();

    } catch {}

  };



  useEffect(() => {

    loadCredentials();

  }, []);



  // Update selected credential if credentials list updates

  useEffect(() => {

    if (selectedCred) {

      const updated = credentials.find(c => c.id === selectedCred.id);

      if (updated) {

        setSelectedCred(updated);

      }

    }

  }, [credentials, selectedCred]);



  const triggerRevealConfirm = (id: number) => {

    setConfirmRevealId(id);

  };



  const handleRevealAfterConfirm = async () => {

    if (confirmRevealId === null) return;

    const id = confirmRevealId;

    setConfirmRevealId(null);

    try {

      const res = await itRequest<{ secret: string }>(`/credentials/${id}/reveal`, { method: 'POST' });

      setRevealed(res.secret);

      loadCredentials();

    } catch {}

  };



  const triggerCopyConfirm = (id: number) => {

    setConfirmCopyId(id);

  };



  const handleCopyAfterConfirm = async () => {

    if (confirmCopyId === null) return;

    const id = confirmCopyId;

    setConfirmCopyId(null);

    try {

      const res = await itRequest<{ secret: string }>(`/credentials/${id}/copy`, { method: 'POST' });

      await navigator.clipboard.writeText(res.secret);

      setCopySuccess(true);

      setTimeout(() => setCopySuccess(false), 2000);

      loadCredentials();

    } catch {}

  };



  // Filter logs for selected credential

  const credentialLogs = useMemo(() => {

    if (!selectedCred) return [];

    return changeLogs.filter(

      (log) =>

        log.entity_type?.toLowerCase() === 'credential' &&

        Number(log.entity_id) === Number(selectedCred.id)

    );

  }, [changeLogs, selectedCred]);



  // Catalog and requests panel components

  const [catalog, setCatalog] = useState<any[]>([]);

  const [requests, setRequests] = useState<any[]>([]);



  const loadAccessCatalog = async () => {

    try {

      const cat = await itRequest<any[]>('/access-catalog');

      const req = await itRequest<any[]>('/access-requests');

      setCatalog(cat);

      setRequests(req);

    } catch {}

  };



  useEffect(() => {

    loadAccessCatalog();

  }, []);



  // Filter catalog by search and type

  const filteredCatalog = useMemo(() => {

    return catalog.filter(c => {

      const matchesSearch = !catalogSearch || 

        c.system_name.toLowerCase().includes(catalogSearch.toLowerCase()) ||

        (c.access_type && c.access_type.toLowerCase().includes(catalogSearch.toLowerCase()));

      const matchesType = !catalogTypeFilter || c.access_type === catalogTypeFilter;

      return matchesSearch && matchesType;

    });

  }, [catalog, catalogSearch, catalogTypeFilter]);



  // Export catalog to CSV (without passwords)

  const handleExportCatalog = () => {

    const headers = ['Sistema', 'Tipo de Acesso', 'URL', 'Status'];

    const rows = filteredCatalog.map(c => [

      c.system_name || '',

      c.access_type || '',

      c.url || '',

      c.is_active ? 'Ativo' : 'Inativo'

    ]);

    

    const csvContent = [headers, ...rows]

      .map(row => row.map(cell => `"${cell}"`).join(','))

      .join('\n');

    

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

    const link = document.createElement('a');

    link.href = URL.createObjectURL(blob);

    link.download = `catalogo-acessos-${new Date().toISOString().split('T')[0]}.csv`;

    link.click();

  };



  const handleAccessRequestAction = async (id: number, action: 'complete' | 'cancel') => {

    try {

      await itRequest(`/access-requests/${id}/${action}`, { method: 'POST' });

      loadAccessCatalog();

    } catch {}

  };



  return (

    <div className="space-y-6">

      <Card className="p-6">

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4 w-full">

          <div className="flex items-center gap-4">

            <KodaMascot variant="security" size="sm" withGlow />

            <div>

              <h2 className="text-xl font-bold text-white flex items-center gap-2">

                🔑 Gestão de Acessos & Cofre de TI

              </h2>

              <p className="text-xs text-slate-400 mt-1 font-medium">

                Controle centralizado de segredos corporativos, senhas, e-mails e catálogo de acessos ISO 9001.

              </p>

            </div>

          </div>

          <div className="flex flex-wrap gap-2">

            <Button size="sm" variant="primary" onClick={onNewVault} leftIcon={<Lock size={14} />}>

              Novo Segredo

            </Button>

            <Button size="sm" variant="secondary" onClick={onNewEmail} leftIcon={<Mail size={14} />}>

              Cadastrar E-mail

            </Button>

            <Button size="sm" variant="secondary" onClick={onNewAccess} leftIcon={<Server size={14} />}>

              Novo Acesso

            </Button>

          </div>

        </div>



        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Cofre de Credenciais */}

          <div className="space-y-3">

            <h3 className="text-base font-bold text-white flex items-center gap-2">

              🔐 Cofre de Senhas

            </h3>

            <p className="text-xs text-slate-400 font-semibold">

              Senhas mascaradas. Clique no card para ver detalhes, revelar ou copiar credenciais sob auditoria.

            </p>

            

            <div className="max-h-[500px] overflow-y-auto pr-1 scrollbar-thin space-y-3">

              {credentials.map((cred) => (

                <div

                  key={cred.id}

                  onClick={() => {

                    setSelectedCred(cred);

                    setRevealed(null);

                  }}

                  className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 hover:border-sky-500/30 hover:bg-slate-950/65 cursor-pointer transition-all flex flex-col gap-2 group text-left"

                >

                  <div className="flex justify-between items-start">

                    <div>

                      <span className="text-[10px] uppercase tracking-wider font-extrabold text-slate-500 block mb-0.5">

                        {cred.system_name}

                      </span>

                      <strong className="text-sm text-slate-200 group-hover:text-sky-400 transition-colors">

                        {cred.title}

                      </strong>

                    </div>

                    <Badge variant="neutral" className="text-[9px] bg-slate-900 border-slate-800 text-slate-400">

                      {cred.visibility_level === 'IT_ADMIN' ? 'Admin TI' : 'Técnico TI'}

                    </Badge>

                  </div>

                  

                  {cred.username && (

                    <span className="text-xs text-slate-400 font-medium">

                      Usuário: <span className="text-slate-300 font-bold">{cred.username}</span>

                    </span>

                  )}



                  <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-900/60 text-[10px] text-slate-500 font-bold">

                    <span>Clique para visualizar</span>

                    <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all text-sky-400" />

                  </div>

                </div>

              ))}

              {credentials.length === 0 && (

                <div className="text-xs text-center py-8 text-slate-500 font-bold">

                  Nenhuma credencial no cofre.

                </div>

              )}

            </div>

          </div>



          {/* E-mails corporativos */}

          <div className="space-y-3">

            <h3 className="text-base font-bold text-white flex items-center gap-2">

              📧 Contas de E-mail

            </h3>

            <p className="text-xs text-slate-400 font-semibold">

              Mapeamento de e-mails corporativos vinculados às credenciais do cofre do Portal Vesper.

            </p>

            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin">

              {corporateEmails.map((email) => (

                <div key={email.id} className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center hover:border-slate-700 transition-colors text-left">

                  <div>

                    <strong className="text-sm text-white block">{email.email_address}</strong>

                    <span className="text-xs text-slate-400 font-medium">Login: {email.login || "não informado"}</span>

                    {email.credential && (

                      <span className="text-xs block text-indigo-400 font-semibold mt-1">

                        🔗 Senha no cofre: {email.credential.title}

                      </span>

                    )}

                  </div>

                  <div className="flex gap-2">

                    <Button

                      size="sm"

                      variant="secondary"

                      onClick={(e) => {

                        e.stopPropagation();

                        onEditEmail(email);

                      }}

                      className="text-[10px] py-1"

                    >

                      Editar

                    </Button>

                    <Button

                      size="sm"

                      variant="danger"

                      onClick={(e) => {

                        e.stopPropagation();

                        onDeleteEmail(email);

                      }}

                      className="text-[10px] py-1"

                    >

                      Excluir

                    </Button>

                  </div>

                </div>

              ))}

              {corporateEmails.length === 0 && (

                <div className="text-xs text-slate-500 text-center py-8 font-bold">

                  Nenhum e-mail cadastrado no sistema.

                </div>

              )}

            </div>

          </div>

        </div>



        {/* Catálogo de Acessos */}

        <div className="mt-8 pt-6 border-t border-slate-800">

          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">

            <h3 className="text-base font-bold text-white flex items-center gap-2">

              📂 Catálogo de Acessos & Pedidos

            </h3>

            <Button size="sm" variant="secondary" onClick={handleExportCatalog} leftIcon={<Download size={14} />}>

              Exportar Catálogo

            </Button>

          </div>

          

          {/* Busca e Filtros */}

          <div className="flex flex-col md:flex-row gap-3 mb-4">

            <div className="flex-1">

              <Input

                placeholder="Buscar ferramenta ou sistema..."

                value={catalogSearch}

                onChange={(e) => setCatalogSearch(e.target.value)}

                leftIcon={<Search size={14} />}

              />

            </div>

            <div className="flex gap-2">

              <Button

                size="sm"

                variant={catalogTypeFilter === '' ? 'primary' : 'secondary'}

                onClick={() => setCatalogTypeFilter('')}

              >

                Todos

              </Button>

              <Button

                size="sm"

                variant={catalogTypeFilter === 'Portal' ? 'primary' : 'secondary'}

                onClick={() => setCatalogTypeFilter('Portal')}

              >

                Portal

              </Button>

              <Button

                size="sm"

                variant={catalogTypeFilter === 'Kanban' ? 'primary' : 'secondary'}

                onClick={() => setCatalogTypeFilter('Kanban')}

              >

                Kanban

              </Button>

              <Button

                size="sm"

                variant={catalogTypeFilter === 'Help Desk' ? 'primary' : 'secondary'}

                onClick={() => setCatalogTypeFilter('Help Desk')}

              >

                Help Desk

              </Button>

              <Button

                size="sm"

                variant={catalogTypeFilter === 'Abacus' ? 'primary' : 'secondary'}

                onClick={() => setCatalogTypeFilter('Abacus')}

              >

                Abacus

              </Button>

            </div>

          </div>

          

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-left">

            <div className="space-y-3">

              <h4 className="font-extrabold text-xs text-slate-400 uppercase tracking-wider">Catálogo de Sistemas</h4>

              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">

                {filteredCatalog.map(c => (

                  <div key={c.id} className="p-3 rounded-xl border border-slate-800 bg-slate-950/30 text-xs text-slate-300 font-bold space-y-1 hover:border-slate-700 transition-colors">

                    <span className="block text-sm font-black text-white">{c.system_name}</span>

                    <span className="block text-slate-400 font-medium">Tipo: {c.access_type || "Nenhum"}</span>

                    {c.url && (

                      <a href={c.url} target="_blank" rel="noreferrer" className="text-indigo-400 block hover:underline mt-1 font-bold">

                        Acessar Sistema ➔

                      </a>

                    )}

                  </div>

                ))}

                {filteredCatalog.length === 0 && <p className="text-xs text-slate-500 text-center font-bold py-8">Nenhum acesso catalogado.</p>}

              </div>

            </div>

            

            <div className="space-y-3">

              <h4 className="font-extrabold text-xs text-slate-400 uppercase tracking-wider">Solicitações de Acesso</h4>

              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">

                {requests.map(r => (

                  <div key={r.id} className="p-3 rounded-xl border border-slate-800 bg-slate-950/30 text-xs text-slate-300 font-bold space-y-2.5">

                    <div>

                      <span className="block text-sm font-black text-white">{r.system_name} - {r.access_type}</span>

                      <span className="block text-slate-400 font-medium mt-1">Motivo: {r.reason}</span>

                      <span className="inline-block text-[10px] text-indigo-400 font-extrabold bg-indigo-950/40 border border-indigo-900/50 px-2 py-0.5 rounded-full mt-1.5">

                        Status: {r.status === 'PENDENTE' ? 'Pendente' : r.status === 'CONCLUIDO' ? 'Concluído' : r.status === 'CANCELADO' ? 'Cancelado' : r.status}

                      </span>

                    </div>

                    {r.status === 'PENDENTE' && (

                      <div className="flex gap-2">

                        <Button size="sm" variant="success" onClick={() => handleAccessRequestAction(r.id, 'complete')} className="text-[10px] py-1 px-2.5">

                          Concluir

                        </Button>

                        <Button size="sm" variant="danger" onClick={() => handleAccessRequestAction(r.id, 'cancel')} className="text-[10px] py-1 px-2.5">

                          Recusar

                        </Button>

                      </div>

                    )}

                  </div>

                ))}

                {requests.length === 0 && <p className="text-xs text-slate-500 text-center font-bold py-8">Nenhuma solicitação ativa.</p>}

              </div>

            </div>

          </div>

        </div>

      </Card>



      {/* CREDENTIAL DETAILS DRAWER */}

      {selectedCred && (

        <Drawer

          open={!!selectedCred}

          title={selectedCred.title}

          description={`Sistema: ${selectedCred.system_name}`}

          onClose={() => {

            setSelectedCred(null);

            setRevealed(null);

          }}

          footer={

            <div className="flex gap-2 justify-end w-full">

              <Button

                variant="danger"

                size="sm"

                onClick={() => {

                  onDeleteVault(selectedCred);

                  setSelectedCred(null);

                }}

              >

                Excluir

              </Button>

              <Button

                variant="secondary"

                size="sm"

                onClick={() => {

                  onEditVault(selectedCred);

                  setSelectedCred(null);

                }}

              >

                Editar Parâmetros

              </Button>

              <Button

                variant="primary"

                size="sm"

                onClick={() => {

                  setSelectedCred(null);

                  setRevealed(null);

                }}

              >

                Fechar Ficha

              </Button>

            </div>

          }

        >

          <div className="space-y-6 text-left">

            {/* Visual Header Banner */}

            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 flex items-center gap-3">

              <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">

                <Shield size={20} />

              </div>

              <div>

                <h4 className="text-xs font-bold text-white uppercase tracking-wider">Nível de Visibilidade</h4>

                <p className="text-xs text-slate-400 mt-0.5">

                  Restrito a: <span className="text-sky-400 font-bold">{selectedCred.visibility_level === 'IT_ADMIN' ? 'Administradores de TI' : 'Técnicos de TI'}</span>

                </p>

              </div>

            </div>



            {/* Credential Data Fields */}

            <div className="space-y-3.5">

              <div>

                <span className="text-[10px] uppercase font-bold text-slate-500">Nome do Sistema / Recurso</span>

                <p className="text-sm font-extrabold text-white mt-0.5">{selectedCred.system_name}</p>

              </div>



              <div>

                <span className="text-[10px] uppercase font-bold text-slate-500">Título Identificador</span>

                <p className="text-sm font-bold text-slate-200 mt-0.5">{selectedCred.title}</p>

              </div>



              {selectedCred.username && (

                <div>

                  <span className="text-[10px] uppercase font-bold text-slate-500">Nome de Usuário / Login</span>

                  <p className="text-sm font-mono font-bold text-sky-400 mt-0.5">{selectedCred.username}</p>

                </div>

              )}



              {selectedCred.url && (

                <div>

                  <span className="text-[10px] uppercase font-bold text-slate-500">URL de Acesso</span>

                  <a

                    href={selectedCred.url}

                    target="_blank"

                    rel="noreferrer"

                    className="text-xs text-indigo-400 hover:underline font-bold flex items-center gap-1 mt-1"

                  >

                    {selectedCred.url} <ExternalLink size={12} />

                  </a>

                </div>

              )}



              {selectedCred.secret_hint && (

                <div>

                  <span className="text-[10px] uppercase font-bold text-slate-500">Dica do Segredo</span>

                  <p className="text-xs text-slate-300 font-semibold bg-slate-950/30 p-2.5 rounded-xl border border-slate-900 mt-1">

                    {selectedCred.secret_hint}

                  </p>

                </div>

              )}

            </div>



            {/* Secret Decryption Panel */}

            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-3">

              <span className="text-[10px] uppercase font-extrabold text-slate-400 tracking-wider flex items-center gap-1.5">

                <Lock size={12} className="text-amber-500" /> Segredo Descriptografado

              </span>

              

              <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-3 rounded-xl font-mono text-sm tracking-widest text-slate-200">

                <span className="select-all">{revealed ? revealed : "••••••••••••"}</span>

                <div className="flex gap-2">

                  {!revealed ? (

                    <button

                      onClick={() => triggerRevealConfirm(selectedCred.id)}

                      className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"

                      title="Revelar Senha"

                    >

                      <Eye size={16} />

                    </button>

                  ) : (

                    <button

                      onClick={() => setRevealed(null)}

                      className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"

                      title="Ocultar Senha"

                    >

                      <EyeOff size={16} />

                    </button>

                  )}

                  <button

                    onClick={() => triggerCopyConfirm(selectedCred.id)}

                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"

                    title="Copiar Senha"

                  >

                    {copySuccess ? <CheckCircle2 size={16} className="text-emerald-500" /> : <Copy size={16} />}

                  </button>

                </div>

              </div>

              <p className="text-[10px] text-amber-500/80 font-bold leading-relaxed">

                ⚠️ Aviso de Conformidade: Cada revelação/cópia de credencial gera uma entrada auditável contendo data, hora e usuário solicitante.

              </p>

            </div>



            {/* Audit Logs Specific to this credential */}

            <div className="space-y-3 border-t border-slate-800 pt-4">

              <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">

                📜 Logs de Auditoria do Segredo

              </h4>

              

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">

                {credentialLogs.map((log) => (

                  <div key={log.id} className="p-3 rounded-xl bg-slate-950/20 border border-slate-900 text-xs flex justify-between items-start gap-3">

                    <div className="space-y-1">

                      <strong className="text-slate-300">{log.action === 'REVEAL' ? 'Senha Revelada' : log.action === 'COPY' ? 'Senha Copiada' : 'Credencial Editada'}</strong>

                      <p className="text-slate-500 text-[10px] font-bold">

                        Por <span className="text-slate-400 font-extrabold">{log.user?.username || 'Sistema'}</span>

                      </p>

                    </div>

                    <time className="text-[9px] text-slate-500 font-bold shrink-0">

                      {new Date(log.created_at).toLocaleString('pt-BR')}

                    </time>

                  </div>

                ))}

                

                {credentialLogs.length === 0 && (

                  <div className="p-4 rounded-xl border border-dashed border-slate-800 text-center text-slate-500 font-bold text-[11px]">

                    Nenhum log de acesso registrado para esta credencial.

                  </div>

                )}

              </div>

            </div>

          </div>

        </Drawer>

      )}

      {confirmRevealId !== null && (

        <ConfirmDialog

          isOpen={true}

          onClose={() => setConfirmRevealId(null)}

          onConfirm={handleRevealAfterConfirm}

          title="Revelar Senha"

          message="Esta ação revelará a senha e criará uma entrada permanente nos logs de auditoria de TI para conformidade ISO 9001. Tem certeza que deseja continuar?"

          confirmText="Revelar Senha"

          variant="primary"

        />

      )}



      {confirmCopyId !== null && (

        <ConfirmDialog

          isOpen={true}

          onClose={() => setConfirmCopyId(null)}

          onConfirm={handleCopyAfterConfirm}

          title="Copiar Senha"

          message="Esta ação copiará a senha para a área de transferência e registrará uma entrada nos logs de auditoria de TI. Tem certeza que deseja continuar?"

          confirmText="Copiar e Registrar"

          variant="primary"

        />

      )}



      {confirmDeleteId !== null && (

        <ConfirmDialog

          isOpen={true}

          onClose={() => setConfirmDeleteId(null)}

          onConfirm={handleDeleteAfterConfirm}

          title="Excluir Credencial"

          message="Esta ação removerá permanentemente a credencial do cofre. Tem certeza que deseja continuar?"

          confirmText="Excluir Permanentemente"

          variant="danger"

        />

      )}

    </div>

  );

};



export default ITCredentials;

