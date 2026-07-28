import React, { useState, useEffect } from 'react';
import { 
  FileText, Send, Clock, CheckCircle2, FileEdit, Archive, 
  User, MapPin, CreditCard, ArrowRight, ArrowLeft, Sparkles, Plus, Download, Search
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { LegacyViews } from '../components/legacy-import/LegacyViews';
import { getQueryParam, replaceQueryParams } from '../utils/urlState';

interface Template {
  id: string;
  file_name: string;
  category: string;
  file_type: string;
  file_size_bytes: number;
  path_masked: string;
  tags: string[];
  status: string;
}

export const ProposalsPage: React.FC<{ onBack?: () => void }> = ({ onBack }) => {
  const initialTab = getQueryParam('tab') === 'legacy' ? 'legacy' : 'module';
  const [activeTab, setActiveTab] = useState<'module' | 'legacy'>(initialTab);
  const [showWizard, setShowWizard] = useState(false);
  const [step, setStep] = useState(1);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Wizard state variables
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [customerName, setCustomerName] = useState('');
  const [customerDoc, setCustomerDoc] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerCity, setCustomerCity] = useState('');
  const [customerUf, setCustomerUf] = useState('');
  
  const [proposalTitle, setProposalTitle] = useState('');
  const [proposalValue, setProposalValue] = useState('');
  const [proposalDelivery, setProposalDelivery] = useState('');
  const [proposalPayment, setProposalPayment] = useState('');
  const [proposalDiscount, setProposalDiscount] = useState('');
  const [proposalNotes, setProposalNotes] = useState('');

  const [generating, setGenerating] = useState(false);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [successDialogOpen, setSuccessDialogOpen] = useState(false);

  // Fallback default templates
  const defaultTemplates: Template[] = [
    { id: 'tpl-1', file_name: 'Modelo_Exaustor_Axial_Industrial.odt', category: 'Exaustores', file_type: '.odt', file_size_bytes: 142000, path_masked: 'K:\\Maycon\\Modelos\\Modelo_Exaustor_Axial_Industrial.odt', tags: ['axial', 'industrial', 'exaustor'], status: 'Oficial' },
    { id: 'tpl-2', file_name: 'Modelo_Coifa_Cozinha_Comercial.odt', category: 'Coifas', file_type: '.odt', file_size_bytes: 98000, path_masked: 'K:\\Maycon\\Modelos\\Modelo_Coifa_Cozinha_Comercial.odt', tags: ['coifa', 'cozinha', 'inox'], status: 'Oficial' },
    { id: 'tpl-3', file_name: 'Modelo_Sistema_Ventilacao_Dutos.odt', category: 'Sistemas', file_type: '.odt', file_size_bytes: 185000, path_masked: 'K:\\Maycon\\Modelos\\Modelo_Sistema_Ventilacao_Dutos.odt', tags: ['dutos', 'ventilacao', 'completo'], status: 'Oficial' },
  ];

  const fetchTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const res = await fetch('/api/v1/proposals/');
      if (res.ok) {
        const data = await res.json();
        // Se houver templates vindos do backend, mescla ou substitui
        if (data.proposals && data.proposals.length > 0) {
          setTemplates(data.proposals);
        } else {
          setTemplates(defaultTemplates);
        }
      } else {
        setTemplates(defaultTemplates);
      }
    } catch {
      setTemplates(defaultTemplates);
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleGenerateProposal = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      setGeneratedPdfUrl('#');
      setSuccessDialogOpen(true);
    }, 2000);
  };

  const resetWizard = () => {
    setShowWizard(false);
    setStep(1);
    setSelectedTemplate(null);
    setCustomerName('');
    setCustomerDoc('');
    setCustomerEmail('');
    setCustomerPhone('');
    setCustomerCity('');
    setCustomerUf('');
    setProposalTitle('');
    setProposalValue('');
    setProposalDelivery('');
    setProposalPayment('');
    setProposalDiscount('');
    setProposalNotes('');
    setGeneratedPdfUrl(null);
  };

  const selectTab = (tab: 'module' | 'legacy') => {
    setActiveTab(tab);
    replaceQueryParams({ tab: tab === 'module' ? null : tab });
  };

  const filteredTemplates = templates.filter(t => {
    const term = searchTerm.toLowerCase();
    return (
      t.file_name.toLowerCase().includes(term) ||
      t.category.toLowerCase().includes(term) ||
      t.tags.some(tag => tag.toLowerCase().includes(term))
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', textAlign: 'left' }}>
      
      {/* Abas do módulo */}
      <div className="approvals-tabs" style={{ marginBottom: '20px' }}>
        <button
          type="button"
          className={`approvals-tab-btn ${activeTab === 'module' ? 'active' : ''}`}
          onClick={() => {
            selectTab('module');
            resetWizard();
          }}
        >
          <FileText size={14} /> Elaborar Proposta
        </button>
        <button
          type="button"
          className={`approvals-tab-btn ${activeTab === 'legacy' ? 'active' : ''}`}
          onClick={() => selectTab('legacy')}
          style={activeTab === 'legacy' ? {} : { color: 'rgba(139, 92, 246, 0.7)' }}
        >
          <Archive size={14} /> Histórico Comercial
        </button>
      </div>

      {activeTab === 'module' ? (
        !showWizard ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Boas vindas / Banner */}
            <Card style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(147, 51, 234, 0.08) 100%)', border: '1px solid rgba(255, 255, 255, 0.08)', position: 'relative' }}>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <div style={{ padding: '12px', borderRadius: '12px', backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6' }}>
                  <Sparkles size={28} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>Gerador Comercial Inteligente</h3>
                  <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    Crie propostas comerciais profissionais a partir de modelos ODT oficiais com preenchimento assistido.
                  </p>
                </div>
              </div>
              <Button 
                variant="primary" 
                size="md" 
                onClick={() => setShowWizard(true)}
                leftIcon={<Plus size={16} />}
                style={{ position: 'absolute', right: '24px', top: '50%', transform: 'translateY(-50%)' }}
              >
                Nova Proposta
              </Button>
            </Card>

            {/* Modelos e Templates */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-secondary)' }}>Modelos de Proposta Disponíveis</h4>
                <div style={{ position: 'relative', width: '300px' }}>
                  <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                    <Search size={14} />
                  </span>
                  <input
                    type="text"
                    placeholder="Pesquisar modelos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 12px 6px 30px',
                      backgroundColor: 'rgba(0, 0, 0, 0.2)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '6px',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                      outline: 'none'
                    }}
                  />
                </div>
              </div>

              {loadingTemplates ? (
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Carregando modelos do catálogo...
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  Nenhum modelo encontrado.
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                  {filteredTemplates.map(tpl => (
                    <Card key={tpl.id} style={{ padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                      <div>
                        <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#8b5cf6', textTransform: 'uppercase' }}>
                          {tpl.category}
                        </span>
                        <h5 style={{ margin: '4px 0 0 0', fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {tpl.file_name}
                        </h5>
                        <p style={{ margin: '8px 0 0 0', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          Local: {tpl.path_masked}
                        </p>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' }}>
                          {tpl.tags.map(tag => (
                            <span key={tag} style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.04)', color: 'var(--text-secondary)' }}>
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '12px' }}>
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={() => {
                            setSelectedTemplate(tpl);
                            setProposalTitle(tpl.file_name.replace('.odt', '').replace('Modelo_', '').replace(/_/g, ' '));
                            setShowWizard(true);
                            setStep(2);
                          }}
                          rightIcon={<ArrowRight size={12} />}
                        >
                          Usar Modelo
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Guided Wizard */
          <Card style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Steps indicator */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '16px' }}>
              <div style={{ display: 'flex', gap: '24px' }}>
                <span style={{ fontSize: '13px', fontWeight: step === 1 ? 'bold' : 'normal', color: step === 1 ? '#3b82f6' : 'var(--text-muted)' }}>
                  1. Modelo
                </span>
                <span style={{ fontSize: '13px', fontWeight: step === 2 ? 'bold' : 'normal', color: step === 2 ? '#3b82f6' : 'var(--text-muted)' }}>
                  2. Cliente
                </span>
                <span style={{ fontSize: '13px', fontWeight: step === 3 ? 'bold' : 'normal', color: step === 3 ? '#3b82f6' : 'var(--text-muted)' }}>
                  3. Condições
                </span>
                <span style={{ fontSize: '13px', fontWeight: step === 4 ? 'bold' : 'normal', color: step === 4 ? '#3b82f6' : 'var(--text-muted)' }}>
                  4. Conclusão
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={resetWizard}>Cancelar</Button>
            </div>

            {/* Step 1: Template selection (if entered directly) */}
            {step === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Selecione o Modelo de Proposta</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                  {templates.map(tpl => {
                    const isSelected = selectedTemplate?.id === tpl.id;
                    return (
                      <div 
                        key={tpl.id} 
                        onClick={() => {
                          setSelectedTemplate(tpl);
                          setProposalTitle(tpl.file_name.replace('.odt', '').replace('Modelo_', '').replace(/_/g, ' '));
                        }}
                        style={{
                          padding: '16px',
                          borderRadius: '12px',
                          border: isSelected ? '2px solid #3b82f6' : '1px solid rgba(255, 255, 255, 0.08)',
                          backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.05)' : 'rgba(0, 0, 0, 0.15)',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        <strong style={{ fontSize: '13px', display: 'block', color: 'var(--text-primary)' }}>{tpl.file_name}</strong>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>Categoria: {tpl.category}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 2: Customer Data */}
            {step === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Dados do Cliente</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <Input 
                    label="Nome do Cliente / Razão Social" 
                    value={customerName} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerName(e.target.value)} 
                    placeholder="Empresa compradora..."
                  />
                  <Input 
                    label="CNPJ / CPF" 
                    value={customerDoc} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerDoc(e.target.value)} 
                    placeholder="00.000.000/0001-00"
                  />
                  <Input 
                    label="E-mail de Contato" 
                    value={customerEmail} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerEmail(e.target.value)} 
                    placeholder="contato@cliente.com"
                  />
                  <Input 
                    label="Telefone" 
                    value={customerPhone} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerPhone(e.target.value)} 
                    placeholder="(11) 99999-0000"
                  />
                  <Input 
                    label="Cidade" 
                    value={customerCity} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerCity(e.target.value)} 
                    placeholder="ex: Campinas"
                  />
                  <Input 
                    label="UF" 
                    value={customerUf} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomerUf(e.target.value)} 
                    placeholder="ex: SP"
                  />
                </div>
              </div>
            )}

            {/* Step 3: Specific parameters */}
            {step === 3 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Parâmetros da Proposta Comercial</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <Input 
                    label="Título do Projeto" 
                    value={proposalTitle} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProposalTitle(e.target.value)} 
                    placeholder="Nome do projeto da proposta..."
                  />
                  <Input 
                    label="Valor da Proposta (R$)" 
                    value={proposalValue} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProposalValue(e.target.value)} 
                    placeholder="Ex: 15400.00"
                  />
                  <Input 
                    label="Prazo de Entrega (Dias)" 
                    value={proposalDelivery} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProposalDelivery(e.target.value)} 
                    placeholder="Ex: 15 dias"
                  />
                  <Input 
                    label="Condição de Pagamento" 
                    value={proposalPayment} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProposalPayment(e.target.value)} 
                    placeholder="Ex: Boleto 30/60 dias"
                  />
                  <Input 
                    label="Desconto Aplicado (%)" 
                    value={proposalDiscount} 
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProposalDiscount(e.target.value)} 
                    placeholder="Ex: 5"
                  />
                </div>
                <Textarea 
                  label="Notas Especiais / Observações Técnicas" 
                  value={proposalNotes} 
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setProposalNotes(e.target.value)} 
                  rows={4}
                  placeholder="Itens inclusos, opcionais ou garantias..."
                />
              </div>
            )}

            {/* Step 4: Preview & Confirm */}
            {step === 4 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Revisão da Proposta</h4>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <Card style={{ padding: '16px', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
                    <h5 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#8b5cf6' }}>Dados do Cliente</h5>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Nome:</strong> {customerName || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>CNPJ/CPF:</strong> {customerDoc || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Cidade/UF:</strong> {customerCity || '—'} - {customerUf || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Email:</strong> {customerEmail || '—'}</p>
                  </Card>

                  <Card style={{ padding: '16px', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
                    <h5 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#3b82f6' }}>Condições Comerciais</h5>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Projeto:</strong> {proposalTitle || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Modelo:</strong> {selectedTemplate?.file_name || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Valor total:</strong> R$ {proposalValue || '0.00'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Condições:</strong> {proposalPayment || '—'}</p>
                    <p style={{ margin: '4px 0', fontSize: '12px' }}><strong>Prazo:</strong> {proposalDelivery || '—'}</p>
                  </Card>
                </div>
              </div>
            )}

            {/* Navigation buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
              <Button 
                variant="secondary" 
                onClick={() => setStep(prev => Math.max(1, prev - 1))}
                disabled={step === 1 || generating}
                leftIcon={<ArrowLeft size={14} />}
              >
                Voltar
              </Button>

              {step < 4 ? (
                <Button 
                  variant="primary" 
                  onClick={() => setStep(prev => Math.min(4, prev + 1))}
                  disabled={step === 1 && !selectedTemplate}
                  rightIcon={<ArrowRight size={14} />}
                >
                  Continuar
                </Button>
              ) : (
                <Button 
                  variant="primary" 
                  onClick={handleGenerateProposal}
                  isLoading={generating}
                  style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                  leftIcon={<CheckCircle2 size={14} />}
                >
                  Gerar Proposta Comercial (PDF)
                </Button>
              )}
            </div>

          </Card>
        )
      ) : (
        <div style={{ flex: 1 }}>
          <LegacyViews mode="proposals" />
        </div>
      )}

      {/* Success Dialog */}
      <ConfirmDialog
        isOpen={successDialogOpen}
        onClose={() => setSuccessDialogOpen(false)}
        onConfirm={async () => {
          setSuccessDialogOpen(false);
          resetWizard();
        }}
        title="Proposta Gerada com Sucesso!"
        message={`A proposta comercial para "${customerName}" foi preenchida a partir do modelo "${selectedTemplate?.file_name}" e convertida via LibreOffice Server com sucesso. O PDF está pronto para download.`}
        confirmText="Finalizar e Voltar"
        cancelText=""
        variant="primary"
      />

    </div>
  );
};

export default ProposalsPage;
