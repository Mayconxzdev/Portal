const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const outDir = path.resolve(__dirname, '..', 'output', 'playwright', 'administration-final-hardening');
const baseUrl = 'http://127.0.0.1:5173';

// Ensure output directory exists
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const mockUsers = [
  {
    id: 1,
    username: 'rafael.martins',
    email: 'rafael.martins@portal.example',
    full_name: 'Rafael Martins',
    department: 'TI',
    job_title: 'Administrador de Redes',
    role_id: 1,
    role_name: 'ADMIN',
    is_active: true,
    must_change_password: false,
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-06-15T18:30:00Z',
    last_login: '2026-06-17T11:00:00Z',
    module_permissions: [
      { module_id: 1, module_code: 'admin', module_name: 'Administração', permission_level: 'ADMIN' },
      { module_id: 2, module_code: 'purchases', module_name: 'Compras', permission_level: 'ADMIN' },
      { module_id: 3, module_code: 'stock', module_name: 'Estoque', permission_level: 'ADMIN' }
    ]
  },
  {
    id: 2,
    username: 'juliana.costa',
    email: 'juliana.costa@portal.example',
    full_name: 'Juliana Costa',
    department: 'Compras',
    job_title: 'Analista de Compras Sênior',
    role_id: 2,
    role_name: 'USER',
    is_active: true,
    must_change_password: false,
    created_at: '2026-02-10T09:00:00Z',
    updated_at: '2026-06-12T14:20:00Z',
    last_login: '2026-06-17T08:15:00Z',
    module_permissions: [
      { module_id: 2, module_code: 'purchases', module_name: 'Compras', permission_level: 'NORMAL' },
      { module_id: 3, module_code: 'stock', module_name: 'Estoque', permission_level: 'READ_ONLY' }
    ]
  },
  {
    id: 5,
    username: 'felipe.andrade',
    email: 'felipe.andrade@portal.example',
    full_name: 'Felipe Andrade',
    department: 'Vendas',
    job_title: 'Assistente Comercial',
    role_id: 2,
    role_name: 'USER',
    is_active: false,
    must_change_password: true,
    created_at: '2026-05-20T11:30:00Z',
    updated_at: '2026-06-14T09:00:00Z',
    last_login: null,
    module_permissions: []
  }
];

const mockRoles = [
  { id: 1, name: 'ADMIN', description: 'Administrador do Portal' },
  { id: 2, name: 'USER', description: 'Usuário Comum' }
];

const mockModules = [
  { id: 1, name: 'Administração', code: 'admin', is_active: true, is_restricted: true },
  { id: 2, name: 'Compras', code: 'purchases', is_active: true, is_restricted: false },
  { id: 3, name: 'Estoque', code: 'stock', is_active: true, is_restricted: false },
  { id: 4, name: 'Chat', code: 'chat', is_active: true, is_restricted: false }
];

const mockAuditLogs = [
  {
    id: 101,
    user_id: 1,
    username: 'rafael.martins',
    action: 'CREATE_USER',
    module: 'admin',
    details: { username: 'mariana.oliveira', role: 'USER' },
    ip_address: '192.168.1.10',
    created_at: '2026-06-17T12:00:00Z'
  },
  {
    id: 102,
    user_id: 1,
    username: 'rafael.martins',
    action: 'admin.session.revoked',
    module: 'admin',
    details: { target_user_id: 2, session_db_id: 8, reason: 'Revogada pela Administracao' },
    ip_address: '192.168.1.10',
    created_at: '2026-06-17T12:05:00Z'
  }
];

const mockSessions = [
  {
    id: 8,
    ip_address: '192.168.1.42',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
    created_at: '2026-06-17T10:00:00Z',
    last_activity_at: '2026-06-17T11:45:00Z',
    expires_at: '2026-06-18T10:00:00Z',
    revoked_at: null,
    revocation_reason: null,
    is_active: true
  }
];

const mockTemporaryAccess = [
  {
    id: 15,
    module_id: 2,
    module_code: 'purchases',
    module_name: 'Compras',
    permission_level: 'NORMAL',
    reason: 'Cobertura de férias de Juliana',
    starts_at: '2026-06-17T12:00:00Z',
    expires_at: '2026-06-24T12:00:00Z',
    status: 'ACTIVE',
    revoked_at: null,
    revocation_reason: null,
    is_effective: true
  }
];

const mockTemporarySubstitutions = [
  {
    id: 4,
    substitute_user_id: 2,
    substitute_username: 'juliana.costa',
    reason: 'Férias regulamentares',
    starts_at: '2026-06-17T12:00:00Z',
    expires_at: '2026-07-02T12:00:00Z',
    status: 'ACTIVE',
    ended_at: null,
    is_effective: true
  }
];

const mockImpact = {
  target_user: { id: 2, username: 'juliana.costa', full_name: 'Juliana Costa', email: 'juliana.costa@portal.example', is_active: true },
  items: [
    { key: 'sessions', label: 'Sessões ativas', count: 1, action: 'Revogar sessões ativas na confirmação', can_auto_apply: true },
    { key: 'temporary_access', label: 'Acessos temporários ativos', count: 1, action: 'Revogar acessos temporários na confirmação', can_auto_apply: true },
    { key: 'kanban', label: 'Cartões Kanban vinculados', count: 4, action: 'Transferir responsável direto para o substituto', can_auto_apply: true },
    { key: 'approvals', label: 'Aprovações pendentes', count: 2, action: 'Criar tarefa de revisão humana', can_auto_apply: false }
  ],
  requires_human_review: true,
  generated_at: '2026-06-17T12:10:00Z'
};

const mockOffboardingCase = {
  id: 42,
  status: 'DRAFT',
  reason: 'Transição consensual',
  replacement_user_id: 1,
  impact_snapshot: mockImpact,
  tasks: [
    { id: 91, title: 'Encerrar sessões ativas (1)', description: 'Revogar sessões ativas na confirmação', status: 'PENDING', requires_human_review: false },
    { id: 92, title: 'Revisar aprovações pendentes (2)', description: 'Criar tarefa de revisão humana', status: 'PENDING', requires_human_review: true }
  ]
};

async function installRoutes(page) {
  await page.route('**/api/v1/ws/notifications', route => route.abort());
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();
    const json = body => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

    if (url.includes('/health')) return json({ status: 'ok' });
    if (url.includes('/auth/me')) return json({ id: 1, username: 'rafael.martins', email: 'rafael.martins@portal.example', role: 'ADMIN', module_permissions: { admin: 'ADMIN' } });
    
    if (url.endsWith('/admin/users') && method === 'GET') return json(mockUsers);
    if (url.endsWith('/admin/roles') && method === 'GET') return json(mockRoles);
    if (url.endsWith('/admin/modules') && method === 'GET') return json(mockModules);
    if (url.endsWith('/admin/audit-logs') && method === 'GET') return json(mockAuditLogs);
    
    if (url.includes('/admin/users/2/sessions') && method === 'GET') return json(mockSessions);
    if (url.includes('/admin/users/2/sessions/8/revoke') && method === 'POST') {
      return json({ ...mockSessions[0], revoked_at: new Date().toISOString(), is_active: false });
    }
    
    if (url.includes('/admin/users/2/temporary-access') && method === 'GET') return json(mockTemporaryAccess);
    if (url.includes('/admin/users/2/temporary-substitutions') && method === 'GET') return json(mockTemporarySubstitutions);
    
    if (url.includes('/admin/users/2/offboarding/impact') && method === 'GET') return json(mockImpact);
    if (url.includes('/admin/users/2/offboarding') && method === 'POST') return json(mockOffboardingCase);
    
    if (url.includes('/admin/offboarding/tasks/92/complete') && method === 'POST') return json({ status: 'success', task_id: 92, task_status: 'COMPLETED' });
    if (url.includes('/admin/offboarding/tasks/92/fail') && method === 'POST') return json({ status: 'success', task_id: 92, task_status: 'FAILED' });
    
    if (url.includes('/admin/offboarding/42/confirm') && method === 'POST') {
      return json({ status: 'success', case: { ...mockOffboardingCase, status: 'CONFIRMED' } });
    }
    if (url.includes('/admin/offboarding/42/cancel') && method === 'POST') {
      return json({ status: 'success', case_id: 42, case_status: 'CANCELLED' });
    }

    if (url.endsWith('/admin/users') && method === 'POST') {
      const body = JSON.parse(request.postData() || '{}');
      if (body.password === '123') {
        return route.fulfill({
          status: 422,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: [
              {
                type: 'string_too_short',
                loc: ['body', 'password'],
                msg: 'A senha temporaria nao pode ser vazia ou conter apenas espacos.',
                input: '123'
              }
            ]
          })
        });
      }
      return json({
        id: 99,
        username: body.username,
        email: body.email,
        full_name: body.full_name,
        role_name: 'USER',
        is_active: true,
        module_permissions: []
      });
    }

    if (url.includes('/master-data/deduplication')) return json([]);

    return json([]);
  });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name) });
}

(async () => {
  const browser = await chromium.launch();
  
  // Theme Claro screenshots
  let context = await browser.newContext();
  let page = await context.newPage();
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER EXCEPTION:', err.stack || err.message));
  await page.setViewportSize({ width: 1440, height: 950 });
  await installRoutes(page);
  
  // 1. Initial page (Light theme)
  await page.goto(`${baseUrl}/admin`);
  await page.waitForTimeout(1000);
  // Set clear theme cookie/localstorage if needed, or rely on UI toggle
  await page.evaluate(() => {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  });
  await page.waitForTimeout(500);
  await shot(page, 'página inicial clara.png');

  // 2. Click "+ Novo usuário" (Step 1)
  await page.getByRole('button', { name: /Novo usuário/i }).first().click();
  await page.waitForTimeout(500);
  await shot(page, 'criação etapa 1.png');

  // Fill out form
  await page.getByLabel(/Nome completo/i).fill('Mariana Oliveira');
  await page.getByLabel(/Nome de usuario/i).fill('mariana.oliveira');
  await page.getByLabel(/Funcao ou setor/i).fill('Financeiro');
  await page.getByLabel(/Senha inicial/i).fill('Vesper-Pass-2026');
  await shot(page, 'criação etapa 1 preenchido.png');

  // 3. Continue to step 2 (Profile suggested)
  await page.getByRole('button', { name: /Continuar/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'perfil sugerido.png');

  // 4. Personalize
  await page.getByRole('button', { name: /Personalizar acessos/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'personalização.png');

  // 5. Review (Step 3)
  await page.getByRole('button', { name: /Continuar/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'revisão.png');

  // Click submit to show success
  await page.getByRole('button', { name: /Criar usuário/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'sucesso.png');

  // Clear form workspace back to idle
  await page.getByRole('button', { name: /Cancelar/i }).click();
  await page.waitForTimeout(500);

  // 6. Open Drawer for user edit (Juliana Costa)
  await page.locator('span', { hasText: 'juliana.costa@portal.example' }).locator('xpath=ancestor::div[3]').getByRole('button', { name: 'Editar' }).click();
  await page.waitForTimeout(500);
  await shot(page, 'drawer Resumo.png');

  // Navigate tabs inside drawer
  const tabs = page.locator('.admin-drawer-tabs');
  await tabs.getByRole('button', { name: 'Acessos', exact: true }).click();
  await page.waitForTimeout(500);
  await shot(page, 'drawer Acessos.png');

  await tabs.getByRole('button', { name: 'Segurança', exact: true }).click();
  await page.waitForTimeout(500);
  await shot(page, 'drawer Segurança.png');

  await tabs.getByRole('button', { name: 'Sessões', exact: true }).click();
  await page.waitForTimeout(500);
  await shot(page, 'sessões.png');

  await tabs.getByRole('button', { name: 'Temp', exact: true }).click();
  await page.waitForTimeout(500);
  await shot(page, 'acesso temporário.png');
  await shot(page, 'substituição.png');

  // Offboarding Tab
  await tabs.getByRole('button', { name: 'Desligamento', exact: true }).click();
  await page.waitForTimeout(500);
  await shot(page, 'impacto de desligamento.png');

  // Create case
  await page.getByLabel(/Justificativa do desligamento/i).fill('Offboarding anual de pessoal');
  await page.getByRole('button', { name: /Criar caso/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'revisão de desligamento.png');

  // Complete one task, show fail on another
  await page.locator('button[title="Marcar como resolvida"]').first().click();
  await page.waitForTimeout(500);
  await shot(page, 'tarefas.png');

  // Type confirmation and lock
  await page.getByLabel(/Confirme digitando o login/i).fill('juliana.costa');
  await page.getByRole('button', { name: /Bloquear e Confirmar/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'resultado.png');

  // Close drawer, open Auditoria tab
  await page.locator('.drawer-panel').getByRole('button', { name: /Fechar/i }).first().click();
  await page.getByRole('button', { name: /Auditoria/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'auditoria.png');

  // Close context
  await context.close();

  // Theme Escuro screenshots
  context = await browser.newContext();
  page = await context.newPage();
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER EXCEPTION:', err.stack || err.message));
  await page.setViewportSize({ width: 1440, height: 950 });
  await installRoutes(page);
  await page.goto(`${baseUrl}/admin`);
  await page.waitForTimeout(1000);
  await page.evaluate(() => {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  });
  await page.waitForTimeout(500);
  await shot(page, 'página inicial escura.png');
  
  // Show error state inside form in clear and dark theme
  await page.getByRole('button', { name: /Novo usuário/i }).first().click();
  await page.getByLabel(/Nome completo/i).fill('Erro Teste');
  await page.getByLabel(/Nome de usuario/i).fill('erro.teste');
  await page.getByLabel(/Funcao ou setor/i).fill('TI');
  await page.getByLabel(/Senha inicial/i).fill('123'); // Triggers mock 422 error
  await page.getByRole('button', { name: /Continuar/i }).click();
  await page.getByRole('button', { name: /Continuar/i }).click();
  await page.getByRole('button', { name: /Criar usuário/i }).click();
  await page.waitForTimeout(500);
  await shot(page, 'erro inline escuro.png');

  // Clear to light mode for clear inline error
  await page.evaluate(() => {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  });
  await page.waitForTimeout(500);
  await shot(page, 'erro inline claro.png');

  await browser.close();
  console.log("Playwright E2E visual captures completed successfully.");
})().catch(err => {
  console.error("Playwright E2E visual check failed:", err);
  process.exit(1);
});
