const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.PORTAL_WEB_URL || 'http://127.0.0.1:5173';
const outDir = path.resolve(__dirname, '..', 'output', 'playwright', 'stock-catalog-intelligence-finalization');

fs.mkdirSync(outDir, { recursive: true });

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true });
}

async function loginIfNeeded(page) {
  await page.goto(`${baseUrl}/stock`);
  await page.waitForLoadState('networkidle').catch(() => {});
  const username = page.locator('input[name="username"], input[autocomplete="username"], input[placeholder*="usu"], input[placeholder*="Usu"], input[placeholder*="login"], input[placeholder*="Login"]').first();
  if (await username.count()) {
    await username.fill(process.env.PORTAL_USER || 'vesper_admin');
    const password = page.locator('input[name="password"], input[type="password"], input[placeholder*="senha"], input[placeholder*="Senha"]').first();
    await password.fill(process.env.PORTAL_PASSWORD || 'portal-dev-only');
    await page.getByRole('button', { name: /entrar|acessar|login/i }).first().click();
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(1200);
  }
}

async function openStock(page) {
  await page.goto(`${baseUrl}/stock`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(/Estoque & Cat[aá]logo/i).first().waitFor({ timeout: 20000 });
}

async function fillFirstVisible(page, selectors, value) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      await locator.fill(value).catch(() => {});
      return true;
    }
  }
  return false;
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  const page = await context.newPage();
  page.setDefaultTimeout(12000);

  await loginIfNeeded(page);
  await openStock(page);
  await shot(page, '01-inicial-clara.png');

  const searchInput = page.getByPlaceholder(/Buscar no cat[aá]logo/i).first();
  if (await searchInput.count()) {
    await searchInput.fill('Arame BTC CL 1,5 mm');
    await page.keyboard.press('Enter');
    await page.waitForLoadState('networkidle').catch(() => {});
  }
  await shot(page, '02-busca-arame.png');

  const firstDetails = page.getByRole('button', { name: /Detalhes|Ver todos os detalhes/i }).first();
  if (await firstDetails.count()) {
    await firstDetails.click();
    await page.waitForTimeout(800);
  } else {
    const firstRow = page.locator('button, [role="button"], .stock-result-row, .stock-row').filter({ hasText: /Arame|Tubo|Papel|Aco|Aço/i }).first();
    if (await firstRow.count()) await firstRow.click().catch(() => {});
  }
  await shot(page, '03-detalhe.png');

  const suppliersTab = page.getByRole('button', { name: /Fornecedores/i }).first();
  if (await suppliersTab.count()) {
    await suppliersTab.click();
    await page.waitForTimeout(500);
  }
  await shot(page, '04-fornecedores.png');

  const updatePrice = page.getByRole('button', { name: /Atualizar Pre[cç]o|Pre[cç]o/i }).first();
  if (await updatePrice.count()) {
    try {
      await updatePrice.scrollIntoViewIfNeeded().catch(() => {});
      await updatePrice.click({ force: true });
      await page.waitForTimeout(500);
      await shot(page, '05-atualizacao-preco.png');
      await fillFirstVisible(page, [
        'input[name="newPrice"]',
        'input[aria-label*="Novo"]',
        'input[placeholder*="Novo"]',
        'input[type="number"]',
        'input[type="text"]'
      ], '14.20');
      await page.waitForTimeout(400);
      await shot(page, '06-preco-preview.png');
    } catch (error) {
      await shot(page, '05-atualizacao-preco-indisponivel.png');
    }
  }

  const historyTab = page.getByRole('button', { name: /Hist[oó]rico/i }).first();
  if (await historyTab.count()) {
    await historyTab.click();
    await page.waitForTimeout(500);
  }
  await shot(page, '07-historico.png');

  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(400);

  const cotar = page.getByRole('button', { name: /^Cotar$|Cotar Produto/i }).first();
  if (await cotar.count()) {
    try {
      await cotar.scrollIntoViewIfNeeded().catch(() => {});
      await cotar.click({ force: true });
      await page.waitForLoadState('networkidle').catch(() => {});
      await page.waitForTimeout(1200);
    } catch (error) {
      await shot(page, '08-handoff-cotar-indisponivel.png');
    }
  }
  await shot(page, '08-handoff-compras.png');

  await page.reload();
  await page.waitForLoadState('networkidle').catch(() => {});
  await shot(page, '09-compras-apos-reload.png');

  await openStock(page);
  if (await searchInput.count().catch(() => 0)) {
    await page.getByPlaceholder(/Buscar no cat[aá]logo/i).first().fill('9,53 mm');
    await page.keyboard.press('Enter');
    await page.waitForLoadState('networkidle').catch(() => {});
  }
  await shot(page, '10-busca-medida.png');

  await openStock(page);
  const stockSearch = page.getByPlaceholder(/Buscar no cat[aá]logo/i).first();
  if (await stockSearch.count()) {
    await stockSearch.fill('FERAÇO');
    await page.keyboard.press('Enter');
    await page.waitForLoadState('networkidle').catch(() => {});
  }
  await shot(page, '11-busca-fornecedor.png');

  await openStock(page);
  const alertsText = page.getByText(/Alerta|Aten[cç][aã]o|Cr[ií]tico|Importante|sem pre[cç]o|sem fornecedor/i).first();
  if (await alertsText.count()) await alertsText.scrollIntoViewIfNeeded().catch(() => {});
  await shot(page, '12-alerta-ou-estado-sem-dados.png');

  await page.evaluate(() => {
    document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  });
  await page.waitForTimeout(400);
  await shot(page, '13-tema-alternado.png');

  await browser.close();
})().catch(error => {
  console.error(error);
  process.exit(1);
});
