import React, { useState, useMemo } from 'react';
import { 
  Search, 
  FileText, 
  BookOpen, 
  ShieldAlert, 
  Wrench, 
  Users, 
  FolderOpen, 
  ExternalLink,
  Download,
  Info,
  Star,
  RefreshCw,
  FolderOpen as FolderIcon,
  ChevronRight
} from 'lucide-react';
import { ModuleHero } from '../components/ui/ModuleHero';
import { ModulePageLayout } from '../components/layout/ModulePageLayout';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { HelpCard } from '../components/layout/HelpCard';
import { Button } from '../components/ui/Button';

interface DocItem {
  id: number;
  title: string;
  category: string;
  type: string;
  size: string;
  updatedAt: string;
  stars: number;
  url: string;
  downloadable: boolean;
}

const initialDocs: DocItem[] = [
  {
    id: 1,
    title: 'Manual do Usuário - Portal Vesper',
    category: 'TI & Acessos',
    type: 'PDF',
    size: '1.8 MB',
    updatedAt: '2026-05-10',
    stars: 5,
    url: '#',
    downloadable: true,
  },
  {
    id: 2,
    title: 'P-Q-002: Controle de Registro de Qualidade',
    category: 'Processos & Qualidade',
    type: 'PDF',
    size: '850 KB',
    updatedAt: '2026-04-15',
    stars: 4,
    url: '#',
    downloadable: true,
  },
  {
    id: 3,
    title: 'Instrução de Trabalho: Configuração de Prensa Hidráulica',
    category: 'Engenharia & Projetos',
    type: 'PDF',
    size: '4.2 MB',
    updatedAt: '2026-03-22',
    stars: 5,
    url: '#',
    downloadable: true,
  },
  {
    id: 4,
    title: 'Política de Segurança da Informação e Senhas',
    category: 'TI & Acessos',
    type: 'PDF',
    size: '1.2 MB',
    updatedAt: '2026-05-18',
    stars: 5,
    url: '#',
    downloadable: true,
  },
  {
    id: 5,
    title: 'Formulário de Solicitação de Reembolso de Viagem',
    category: 'RH & Integração',
    type: 'XLSX',
    size: '340 KB',
    updatedAt: '2026-01-10',
    stars: 3,
    url: '#',
    downloadable: true,
  },
  {
    id: 6,
    title: 'Onboarding Portal Vesper - Guia de Primeiros Passos',
    category: 'RH & Integração',
    type: 'PDF',
    size: '2.5 MB',
    updatedAt: '2026-05-01',
    stars: 5,
    url: '#',
    downloadable: true,
  },
  {
    id: 7,
    title: 'Norma Técnica NTS-044: Padrão de Soldagem de Flanges',
    category: 'Engenharia & Projetos',
    type: 'PDF',
    size: '3.1 MB',
    updatedAt: '2026-02-28',
    stars: 4,
    url: '#',
    downloadable: true,
  }
];

const categories = [
  {
    name: 'Engenharia & Projetos',
    description: 'Desenhos industriais, normas técnicas e manuais de fabricação.',
    icon: <Wrench size={20} />,
    color: 'var(--color-primary, #6366f1)',
    bg: 'rgba(99, 102, 241, 0.08)',
    border: 'rgba(99, 102, 241, 0.15)',
    count: 145,
  },
  {
    name: 'Processos & Qualidade',
    description: 'Instruções de Trabalho (IT), controle de qualidade e registros.',
    icon: <BookOpen size={20} />,
    color: '#34d399',
    bg: 'rgba(52, 211, 153, 0.08)',
    border: 'rgba(52, 211, 153, 0.15)',
    count: 98,
  },
  {
    name: 'TI & Acessos',
    description: 'Tutoriais de infraestrutura, links de servidores, políticas de TI.',
    icon: <ShieldAlert size={20} />,
    color: '#a78bfa',
    bg: 'rgba(167, 139, 250, 0.08)',
    border: 'rgba(167, 139, 250, 0.15)',
    count: 34,
  },
  {
    name: 'RH & Integração',
    description: 'Formulários corporativos, benefícios e guia de onboarding.',
    icon: <Users size={20} />,
    color: '#f43f5e',
    bg: 'rgba(244, 63, 94, 0.08)',
    border: 'rgba(244, 63, 94, 0.15)',
    count: 52,
  }
];

export const FilesKnowledgePage: React.FC<{ onBack?: () => void }> = ({ onBack }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [downloadCount, setDownloadCount] = useState<Record<number, number>>({});
  const [showToast, setShowToast] = useState(false);
  const [toastMsg, setToastMsg] = useState('');

  const handleDownload = (doc: DocItem) => {
    setDownloadCount(prev => ({
      ...prev,
      [doc.id]: (prev[doc.id] || 0) + 1
    }));
    setToastMsg(`Baixando arquivo: ${doc.title}`);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleCategorySelect = (categoryName: string) => {
    if (selectedCategory === categoryName) {
      setSelectedCategory(null);
    } else {
      setSelectedCategory(categoryName);
    }
  };

  const filteredDocs = useMemo(() => {
    return initialDocs.filter((doc) => {
      const matchSearch = searchTerm.trim() === '' || 
        doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.type.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchCategory = !selectedCategory || doc.category === selectedCategory;

      return matchSearch && matchCategory;
    });
  }, [searchTerm, selectedCategory]);

  const asideContent = (
    <>
      <section className="module-side-card glass-card" style={{ padding: 18 }}>
        <h3 className="module-side-title" style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 12px 0' }}>
          <FolderOpen size={16} style={{ color: 'var(--color-primary, #6366f1)' }} />
          <span>Diretórios na Rede</span>
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.45, margin: '0 0 14px 0' }}>
          Você pode acessar os arquivos brutos diretamente no servidor de arquivos configurado:
        </p>
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={networkPathStyle}>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Projetos e Engenharia</span>
            <code style={codeStyle}>\\fileserver.local\engenharia</code>
          </div>
          <div style={networkPathStyle}>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Normas e Qualidade</span>
            <code style={codeStyle}>\\fileserver.local\qualidade</code>
          </div>
          <div style={networkPathStyle}>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Padrões de TI</span>
            <code style={codeStyle}>\\fileserver.local\ti-manuais</code>
          </div>
        </div>
      </section>
      
      <HelpCard 
        description="Esta biblioteca corporativa unifica os arquivos. Todos os uploads feitos no Kanban ou nos chamados de TI são anexados de forma inteligente nas pastas dos setores correspondentes."
        actionLabel="Entenda a LGPD"
        onAction={() => {
          setToastMsg("As diretrizes da LGPD estão ativas nesta biblioteca.");
          setShowToast(true);
          setTimeout(() => setShowToast(false), 3000);
        }}
      />
    </>
  );

  return (
    <ModulePageLayout className="files-knowledge-page" aside={asideContent}>
      {showToast && (
        <div style={toastStyle}>
          <Info size={16} />
          <span>{toastMsg}</span>
        </div>
      )}

      <ModuleHero
        accent="cyan"
        icon={<FolderIcon size={28} />}
        title="Arquivos & Biblioteca de Conhecimento"
        description="Encontre de forma simples as instruções de trabalho, manuais técnicos de TI, processos da qualidade e arquivos gerais."
        kodaMessage="Estes são os documentos da base oficial. Digite no buscador para encontrar rapidamente."
        compact={selectedCategory !== null || searchTerm !== ''}
        actions={
          <Button 
            variant="secondary" 
            onClick={() => {
              setSearchTerm('');
              setSelectedCategory(null);
            }} 
            leftIcon={<RefreshCw size={14} />}
          >
            Limpar Filtros
          </Button>
        }
      />

      {/* Busca Proeminente - Vesper Focus Workspace */}
      <Card variant="glass" style={{ padding: '24px 20px', marginBottom: 20 }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: 15, fontWeight: 600, color: '#f8fafc' }}>
          O que você está procurando hoje?
        </h3>
        <div style={{ position: 'relative' }}>
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Pesquise por manuais de TI, normas técnicas de flanges, procedimentos da qualidade..."
            style={{ 
              marginBottom: 0, 
              paddingLeft: 44, 
              height: 48, 
              fontSize: 15, 
              background: 'rgba(15, 23, 42, 0.4)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          />
          <Search 
            size={20} 
            style={{ 
              position: 'absolute', 
              left: 16, 
              top: '50%', 
              transform: 'translateY(-50%)', 
              color: '#64748b' 
            }} 
          />
        </div>
      </Card>

      {/* Grid de Categorias */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 14px 0', fontSize: 14, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Categorias Principais
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat.name;
            return (
              <article 
                key={cat.name} 
                onClick={() => handleCategorySelect(cat.name)}
                style={{ 
                  cursor: 'pointer',
                  padding: 16,
                  borderRadius: 12,
                  background: isSelected ? 'rgba(255, 255, 255, 0.04)' : cat.bg,
                  border: isSelected ? `2px solid ${cat.color}` : `1px solid ${cat.border}`,
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? `0 0 12px ${cat.border}` : 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
                className="category-card-hover"
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ color: cat.color, padding: 6, borderRadius: 8, background: 'rgba(0,0,0,0.2)' }}>
                    {cat.icon}
                  </div>
                  <span style={{ fontSize: 12, color: cat.color, fontWeight: 700 }}>
                    {cat.count} docs
                  </span>
                </div>
                <h4 style={{ margin: '4px 0 0', color: '#f8fafc', fontSize: 14, fontWeight: 600 }}>
                  {cat.name}
                </h4>
                <p style={{ margin: 0, color: '#94a3b8', fontSize: 12, lineHeight: 1.4 }}>
                  {cat.description}
                </p>
              </article>
            );
          })}
        </div>
      </div>

      {/* Listagem de Documentos Filtrados */}
      <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: '#f8fafc', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>Arquivos Encontrados ({filteredDocs.length})</span>
            {selectedCategory && (
              <Badge variant="primary" style={{ textTransform: 'none' }}>
                {selectedCategory}
              </Badge>
            )}
          </h3>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Total indexado: {initialDocs.length} documentos
          </span>
        </div>

        <div className="admin-user-card-list">
          {filteredDocs.map((doc) => (
            <article 
              key={doc.id} 
              className="admin-user-row glass-card" 
              style={{ 
                margin: 0, 
                borderRadius: 0, 
                border: 'none', 
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                padding: '12px 18px',
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1.8fr) minmax(0, 0.8fr) 100px 100px auto',
                alignItems: 'center',
                gap: 16
              }}
            >
              {/* Nome do arquivo */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <FileText size={18} style={{ color: doc.category === 'TI & Acessos' ? '#a78bfa' : doc.category === 'Processos & Qualidade' ? '#34d399' : doc.category === 'RH & Integração' ? '#f43f5e' : '#6366f1', flexShrink: 0 }} />
                <div style={{ minWidth: 0 }}>
                  <strong style={{ color: '#fff', fontSize: 13, display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {doc.title}
                  </strong>
                  <span style={{ fontSize: 11, color: '#64748b' }}>Atualizado em {new Date(doc.updatedAt).toLocaleDateString('pt-BR')}</span>
                </div>
              </div>

              {/* Categoria */}
              <div>
                <span style={{ 
                  fontSize: 12, 
                  color: doc.category === 'TI & Acessos' ? '#c084fc' : doc.category === 'Processos & Qualidade' ? '#34d399' : doc.category === 'RH & Integração' ? '#fb7185' : '#818cf8',
                  fontWeight: 500
                }}>
                  {doc.category}
                </span>
              </div>

              {/* Tamanho e Formato */}
              <div>
                <Badge variant="neutral" style={{ fontSize: 10, fontFamily: 'monospace' }}>
                  {doc.type} · {doc.size}
                </Badge>
              </div>

              {/* Estrelas / Popularidade */}
              <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star 
                    key={i} 
                    size={11} 
                    fill={i < doc.stars ? '#fbbf24' : 'none'} 
                    color={i < doc.stars ? '#fbbf24' : '#334155'} 
                  />
                ))}
              </div>

              {/* Botões de Ação */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDownload(doc)}
                  leftIcon={<Download size={13} />}
                >
                  <span>Baixar {downloadCount[doc.id] ? `(${downloadCount[doc.id]})` : ''}</span>
                </Button>
                <a 
                  className="btn btn-ghost btn-sm"
                  href={doc.url}
                  onClick={(e) => {
                    e.preventDefault();
                    setToastMsg(`Visualizando arquivo: ${doc.title}`);
                    setShowToast(true);
                    setTimeout(() => setShowToast(false), 3000);
                  }}
                  style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <ChevronRight size={13} />
                </a>
              </div>
            </article>
          ))}

          {filteredDocs.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <p style={{ color: '#94a3b8', fontSize: 13, margin: '0 0 10px 0' }}>Nenhum documento encontrado para a busca ou filtro selecionado.</p>
              <Button size="sm" variant="ghost" onClick={() => { setSearchTerm(''); setSelectedCategory(null); }}>
                Limpar filtros de busca
              </Button>
            </div>
          )}
        </div>
      </Card>
    </ModulePageLayout>
  );
};

const networkPathStyle: React.CSSProperties = {
  background: 'rgba(0, 0, 0, 0.2)',
  border: '1px solid rgba(255, 255, 255, 0.04)',
  borderRadius: 8,
  padding: '8px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: 4
};

const codeStyle: React.CSSProperties = {
  fontFamily: 'monospace',
  fontSize: 12,
  color: '#38bdf8',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis'
};

const toastStyle: React.CSSProperties = {
  position: 'fixed',
  right: 24,
  bottom: 24,
  zIndex: 10000,
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  padding: '14px 18px',
  borderRadius: 10,
  background: 'rgba(6, 182, 212, 0.95)',
  color: '#fff',
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
  fontSize: 14,
  fontWeight: 500,
  animation: 'slideIn 0.2s ease'
};

export default FilesKnowledgePage;
