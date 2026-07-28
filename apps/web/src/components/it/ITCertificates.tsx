import React, { useState, useMemo } from 'react';
import { ShieldCheck, Plus, Clock, RefreshCw, AlertTriangle, Key, Search } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { EmptyState } from '../ui/EmptyState';
import { KodaMascot } from '../ui/KodaMascot';
import { itRequest } from './itApi';

export interface ITCertificatesProps {
  certificates: any[];
  onNew: () => void;
  onEdit: (cert: any) => void;
  onReload: () => void;
  setMessage: (msg: string) => void;
  onDelete: (cert: any) => void;
}

export const ITCertificates: React.FC<ITCertificatesProps> = ({
  certificates,
  onNew,
  onEdit,
  onReload,
  setMessage,
  onDelete,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const handleRenew = async (id: number) => {
    try {
      await itRequest(`/certificates/${id}/create-ticket`, { method: 'POST' });
      setMessage("Chamado de renovação de licença/certificado aberto com sucesso!");
      onReload();
    } catch {
      setMessage("Erro ao solicitar renovação.");
    }
  };

  // real-time filter
  const filteredCerts = useMemo(() => {
    return certificates.filter(cert => {
      const query = searchTerm.toLowerCase();
      return (
        cert.name?.toLowerCase().includes(query) ||
        cert.domain_or_system?.toLowerCase().includes(query) ||
        cert.issuer?.toLowerCase().includes(query) ||
        cert.provider?.toLowerCase().includes(query)
      );
    });
  }, [certificates, searchTerm]);

  // Separate certificates and licenses
  const isLicense = (cert: any) => {
    const nameLower = (cert.name || '').toLowerCase();
    const systemLower = (cert.domain_or_system || '').toLowerCase();
    return (
      nameLower.includes('licença') ||
      nameLower.includes('licenca') ||
      nameLower.includes('license') ||
      nameLower.includes('microsoft') ||
      nameLower.includes('office') ||
      nameLower.includes('antivirus') ||
      nameLower.includes('windows') ||
      nameLower.includes('software') ||
      systemLower.includes('software') ||
      !systemLower.includes('.')
    );
  };

  const sslCertificates = filteredCerts.filter(c => !isLicense(c));
  const softwareLicenses = filteredCerts.filter(c => isLicense(c));

  // Determine Koda warning status
  const expiringOrExpired = certificates.filter(cert => {
    const isExpired = new Date(cert.expires_at) < new Date();
    const isExpiring = !isExpired && (new Date(cert.expires_at).getTime() - new Date().getTime()) < (30 * 24 * 60 * 60 * 1000);
    return isExpired || isExpiring;
  });

  const hasAlert = expiringOrExpired.length > 0;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              🛡️ Certificados & Licenças Corporativas
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-medium">
              Controle de chaves SSL, tokens e datas de validade para auditoria técnica e conformidade.
            </p>
          </div>
          <Button size="sm" variant="primary" onClick={onNew} leftIcon={<Plus size={14} />}>
            Novo Certificado / Licença
          </Button>
        </div>

        {/* Koda Health Banner */}
        <div className={`p-4 rounded-2xl border flex items-center gap-4 mb-6 ${
          hasAlert 
            ? 'bg-rose-950/20 border-rose-500/30' 
            : 'bg-emerald-950/20 border-emerald-500/30'
        }`}>
          <KodaMascot variant={hasAlert ? 'alert' : 'success'} size="sm" withGlow />
          <div>
            <h4 className={`text-sm font-bold ${hasAlert ? 'text-rose-450' : 'text-emerald-400'}`}>
              {hasAlert ? 'Atenção aos Vencimentos!' : 'Segurança em Dia!'}
            </h4>
            <p className="text-xs text-slate-300 font-semibold mt-0.5">
              {hasAlert 
                ? `Existem ${expiringOrExpired.length} itens vencidos ou próximos de vencer em menos de 30 dias. Ação necessária!`
                : 'Todos os certificados e licenças mapeados estão ativos e dentro da validade.'}
            </p>
          </div>
        </div>

        {/* Filter Input */}
        <div className="flex items-center gap-2 border border-white/5 bg-slate-950/40 px-3 py-1 rounded-xl mb-6 max-w-md">
          <Search size={16} className="text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filtrar por nome, emissor, provedor ou domínio..."
            className="w-full bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 py-1.5"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Section: Certificados SSL */}
          <div className="space-y-4">
            <h3 className="text-sm font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              🌐 Certificados SSL & Domínios
            </h3>
            <div className="space-y-3">
              {sslCertificates.map(cert => {
                const isExpired = new Date(cert.expires_at) < new Date();
                const isExpiring = !isExpired && (new Date(cert.expires_at).getTime() - new Date().getTime()) < (30 * 24 * 60 * 60 * 1000);

                return (
                  <div key={cert.id} className="p-4 rounded-xl border border-slate-800 bg-slate-950/30 hover:border-slate-700 transition-colors flex flex-col justify-between gap-3 text-left">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <strong className="text-sm text-white block">{cert.name}</strong>
                        <span className="text-[11px] text-slate-405 block mt-0.5">Domínio: <span className="text-slate-300 font-bold">{cert.domain_or_system}</span></span>
                      </div>
                      <Badge variant={isExpired ? 'danger' : isExpiring ? 'warning' : 'success'} className="text-[10px]">
                        {isExpired ? 'EXPIRADO' : isExpiring ? 'VENCENDO' : 'VÁLIDO'}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-slate-500 font-bold flex justify-between items-center border-t border-slate-900 pt-2">
                      <span>Emissor: {cert.issuer || '-'}</span>
                      <span className="flex items-center gap-1 text-slate-400 font-bold"><Clock size={11} /> {new Date(cert.expires_at).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <Button size="sm" variant="secondary" onClick={() => onEdit(cert)} className="text-[10px] py-1 px-2.5">
                        Editar
                      </Button>
                      <Button size="sm" variant="primary" onClick={() => handleRenew(cert.id)} className="text-[10px] py-1 px-2.5" leftIcon={<RefreshCw size={10} />}>
                        Renovar
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => onDelete(cert)} className="text-[10px] py-1 px-2.5">
                        Excluir
                      </Button>
                    </div>
                  </div>
                );
              })}
              {sslCertificates.length === 0 && (
                <p className="text-xs text-slate-500 font-bold text-center py-6">Nenhum certificado encontrado.</p>
              )}
            </div>
          </div>

          {/* Section: Licenças de Software */}
          <div className="space-y-4">
            <h3 className="text-sm font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              🔑 Licenças de Software & Assinaturas
            </h3>
            <div className="space-y-3">
              {softwareLicenses.map(cert => {
                const isExpired = new Date(cert.expires_at) < new Date();
                const isExpiring = !isExpired && (new Date(cert.expires_at).getTime() - new Date().getTime()) < (30 * 24 * 60 * 60 * 1000);

                return (
                  <div key={cert.id} className="p-4 rounded-xl border border-slate-800 bg-slate-950/30 hover:border-slate-700 transition-colors flex flex-col justify-between gap-3 text-left">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <strong className="text-sm text-white block">{cert.name}</strong>
                        <span className="text-[11px] text-slate-405 block mt-0.5">Sistema: <span className="text-slate-300 font-bold">{cert.domain_or_system}</span></span>
                      </div>
                      <Badge variant={isExpired ? 'danger' : isExpiring ? 'warning' : 'success'} className="text-[10px]">
                        {isExpired ? 'EXPIRADO' : isExpiring ? 'VENCENDO' : 'VÁLIDO'}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-slate-500 font-bold flex justify-between items-center border-t border-slate-900 pt-2">
                      <span>Provedor: {cert.provider || '-'}</span>
                      <span className="flex items-center gap-1 text-slate-400 font-bold"><Clock size={11} /> {new Date(cert.expires_at).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <Button size="sm" variant="secondary" onClick={() => onEdit(cert)} className="text-[10px] py-1 px-2.5">
                        Editar
                      </Button>
                      <Button size="sm" variant="primary" onClick={() => handleRenew(cert.id)} className="text-[10px] py-1 px-2.5" leftIcon={<RefreshCw size={10} />}>
                        Solicitar Renovação
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => onDelete(cert)} className="text-[10px] py-1 px-2.5">
                        Excluir
                      </Button>
                    </div>
                  </div>
                );
              })}
              {softwareLicenses.length === 0 && (
                <p className="text-xs text-slate-500 font-bold text-center py-6">Nenhuma licença encontrada.</p>
              )}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ITCertificates;
