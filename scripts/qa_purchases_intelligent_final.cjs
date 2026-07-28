const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

let AxeBuilder = null;
try {
  ({ AxeBuilder } = require('@axe-core/playwright'));
} catch {
  AxeBuilder = null;
}

const baseUrl = process.env.PORTAL_WEB_URL || process.env.PURCHASES_QA_BASE_URL || 'http://127.0.0.1:5173';
const outDir = path.resolve(__dirname, '..', 'output', 'playwright', 'purchases-intelligent-final');
fs.mkdirSync(outDir, { recursive: true });

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true });
}

async function loginIfNeeded(page) {
  await page.goto(`${baseUrl}/purchases`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await Promise.race([
    page.locator('#username, input[name="username"], input[autocomplete="username"]').first().waitFor({ timeout: 10000 }).catch(() => null),
    page.getByRole('heading', { name: /Compras/i }).first().waitFor({ timeout: 10000 }).catch(() => null),
  ]);
  const username = page.locator('#username, input[name="username"], input[autocomplete="username"], input[placeholder*="usu" i], input[placeholder*="login" i]').first();
  if (await username.count()) {
    await username.fill(process.env.PORTAL_USER || 'vesper_admin');
    const password = page.locator('#password, input[name="password"], input[type="password"], input[placeholder*="senha" i]').first();
    await password.fill(process.env.PORTAL_PASSWORD || 'portal-dev-only');
    await page.getByRole('button', { name: /entrar|acessar|login/i }).first().click();
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.getByRole('heading', { name: /Compras/i }).first().waitFor({ timeout: 20000 }).catch(async () => {
      await shot(page, 'blocked-login.png');
      throw new Error(`Login QA nao abriu Compras. Texto atual: ${(await page.locator('body').innerText().catch(() => '')).slice(0, 500)}`);
    });
  }
}

async function openPurchases(page) {
  await page.goto(`${baseUrl}/purchases`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByRole('heading', { name: /Compras/i }).first().waitFor({ timeout: 20000 }).catch(async () => {
    await shot(page, 'blocked-open-purchases.png');
    throw new Error(`Nao abriu Compras. URL: ${page.url()}. Texto atual: ${(await page.locator('body').innerText().catch(() => '')).slice(0, 500)}`);
  });
}

async function analyzeNeed(page, text) {
  await page.getByRole('button', { name: /Nova compra/i }).first().click();
  const input = page.locator('#need-pasted-list').first();
  await input.waitFor({ timeout: 12000 });
  await input.fill(text);
  await shot(page, '03-nova-compra-vazia.png');
  await page.getByRole('button', { name: /Analisar antes de criar/i }).click();
  await page.waitForTimeout(1200);
}

async function runAxe(page, name) {
  if (!AxeBuilder) return;
  const results = await new AxeBuilder({ page }).analyze();
  fs.writeFileSync(path.join(outDir, `${name}.axe.json`), JSON.stringify(results.violations, null, 2));
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  const page = await context.newPage();
  page.setDefaultTimeout(14000);

  await loginIfNeeded(page);
  await openPurchases(page);
  await shot(page, '01-central-light.png');
  await runAxe(page, '01-central-light');

  const darkToggle = page.getByRole('button', { name: /tema|escuro|claro|dark|light/i }).first();
  if (await darkToggle.count()) {
    await darkToggle.click().catch(() => {});
    await page.waitForTimeout(800);
  }
  await shot(page, '02-central-dark.png');

  await openPurchases(page);
  await analyzeNeed(page, '2 memorias RAM DDR5 8 GB para o computador de um colaborador, ate R$ 5000');
  await shot(page, '04-memoria-externa.png');

  await openPurchases(page);
  await analyzeNeed(page, 'Arame BTC CL 1,5 mm');
  await shot(page, '05-arame-interno.png');

  await openPurchases(page);
  await analyzeNeed(page, 'cabo pp 3x2,5');
  await shot(page, '06-compra-ambigua.png');

  await openPurchases(page);
  await analyzeNeed(page, '2 memorias RAM DDR5 8 GB ate R$ 5000\n1 Arame BTC CL 1,5 mm');
  await shot(page, '07-compra-mista.png');

  const createButton = page.getByRole('button', { name: /^Criar compra$/i }).first();
  if (await createButton.count()) {
    await createButton.click().catch(() => {});
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(1200);
    await shot(page, '08-criacao-idempotente.png');
  }

  const firstNeed = page.locator('.purchase-need-card').first();
  if (await firstNeed.count()) {
    await firstNeed.click().catch(() => {});
    await page.waitForTimeout(600);
  }
  await shot(page, '09-workspace-central.png');

  const searchExternal = page.getByRole('button', { name: /Pesquisar|Adicionar opcao|Adicionar opção/i }).first();
  if (await searchExternal.count()) {
    await searchExternal.click().catch(() => {});
    await page.waitForTimeout(1000);
    await shot(page, '10-pesquisa-progressiva.png');
  }

  const whyButton = page.getByRole('button', { name: /Por que recomendamos|Como estes dados foram confirmados/i }).first();
  if (await whyButton.count()) {
    await whyButton.click().catch(() => {});
    await page.waitForTimeout(500);
    await shot(page, '11-recomendacao-e-evidencia.png');
  }

  const approvalButton = page.getByRole('button', { name: /Pedir aprovacao|Pedir aprovação|Enviar para aprovacao|Enviar para aprovação/i }).first();
  if (await approvalButton.count()) {
    await approvalButton.click().catch(() => {});
    await page.waitForTimeout(800);
    await shot(page, '12-aprovacao-por-item.png');
  }

  const rfqButton = page.getByRole('button', { name: /Cotacao direta|Cotação direta|Preparar cotacao|Preparar cotação|Revisar fornecedores/i }).first();
  if (await rfqButton.count()) {
    await rfqButton.click().catch(() => {});
    await page.waitForTimeout(800);
    await shot(page, '13-cotacao-fornecedor.png');
  }

  const orderButton = page.getByRole('button', { name: /Registrar Compra|Registrar pedido|Marcar como comprado/i }).first();
  if (await orderButton.count()) {
    await orderButton.click().catch(() => {});
    await page.waitForTimeout(600);
    await shot(page, '14-pedido.png');
  }

  const deliveryButton = page.getByRole('button', { name: /Receber Entrega|Receber parcialmente|Registrar recebimento/i }).first();
  if (await deliveryButton.count()) {
    await deliveryButton.click().catch(() => {});
    await page.waitForTimeout(600);
    await shot(page, '15-entrega-parcial.png');
  }

  await shot(page, '16-final-sem-abas-antigas.png');
  await browser.close();
})().catch(error => {
  console.error(error);
  process.exit(1);
});
