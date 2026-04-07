/**
 * 分路链式 V5.0 · 前端全流程 E2E 测试
 *
 * 模拟人手工操作：打开浏览器 → 登录 → 逐个模块操作 → 验证结果
 * 每步自动截图，失败时录屏。
 *
 * 运行: npx playwright test
 * 查看报告: npx playwright show-report
 */
import { test, expect, type Page } from '@playwright/test';

const uid = () => Math.random().toString(36).slice(2, 8);

// ── 登录辅助 ──────────────────────────────────────────────────────

async function login(page: Page) {
  await page.goto('/login');
  await page.fill('input[type="text"]:first-of-type', 'demo');
  // 第二个 text input 是用户名
  const inputs = page.locator('input[type="text"]');
  await inputs.nth(0).fill('demo');
  await inputs.nth(1).fill('admin');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  // 等待跳转到首页
  await page.waitForURL('/', { timeout: 10000 });
}

// ── 测试 ──────────────────────────────────────────────────────────

test.describe('完整业务流程测试', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('01 驾驶舱加载', async ({ page }) => {
    // 验证驾驶舱标题
    await expect(page.locator('text=领导驾驶舱')).toBeVisible();
    // 验证有 KPI 卡片
    await expect(page.locator('text=今日营收')).toBeVisible();
    await expect(page.locator('text=OEE 综合效率')).toBeVisible();
  });

  test('02 PLM 产品管理 — 浏览+新建', async ({ page }) => {
    // 导航到 PLM
    await page.click('text=产品生命周期');
    await expect(page.locator('text=产品生命周期管理')).toBeVisible();

    // 导航到产品页面
    await page.goto('/plm/products');
    await page.waitForSelector('table', { timeout: 10000 });
    // 验证表头存在
    await expect(page.locator('text=产品编码')).toBeVisible();
  });

  test('03 PLM 客户管理 — 新建客户', async ({ page }) => {
    await page.click('text=产品生命周期');
    await page.click('text=CRM 客户管理');
    await page.waitForURL('**/plm/customers');

    await page.click('text=新建客户');
    await page.waitForTimeout(500);

    // 填写表单
    const inputs = page.locator('form input');
    await inputs.nth(0).fill(`C-${uid()}`);  // 编码
    await inputs.nth(1).fill('Playwright测试客户');  // 名称

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);
  });

  test('04 MFG 生产工单 — 浏览', async ({ page }) => {
    await page.click('text=生产制造');
    await expect(page.locator('text=生产制造管理')).toBeVisible();

    await page.click('text=生产工单');
    await page.waitForURL('**/mfg/work-orders');
    await expect(page.locator('text=生产工单')).toBeVisible();
  });

  test('05 MFG 质量检验 — 浏览', async ({ page }) => {
    await page.click('text=生产制造');
    await page.click('text=质量检验');
    await page.waitForURL('**/mfg/qc');
    await expect(page.locator('text=质量检验')).toBeVisible();
  });

  test('06 MFG 设备管理 — 新建设备', async ({ page }) => {
    await page.click('text=生产制造');
    await page.click('text=设备管理');
    await page.waitForURL('**/mfg/equipment');

    await page.click('text=新建设备');
    await page.waitForTimeout(500);

    const inputs = page.locator('form input');
    await inputs.nth(0).fill(`EQ-${uid()}`);
    await inputs.nth(1).fill('Playwright测试设备');

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);
  });

  test('07 MFG 安全生产 — 浏览', async ({ page }) => {
    await page.click('text=生产制造');
    await page.click('text=安全生产');
    await page.waitForURL('**/mfg/safety');
    await expect(page.locator('text=安全生产')).toBeVisible();
  });

  test('08 SCM 供应商 — 新建+搜索', async ({ page }) => {
    await page.click('text=供应链');
    await page.click('text=供应商管理');
    await page.waitForURL('**/scm/suppliers');

    // 新建
    await page.click('text=新建供应商');
    await page.waitForTimeout(500);

    const inputs = page.locator('form input');
    const code = `S-${uid()}`;
    await inputs.nth(0).fill(code);
    await inputs.nth(1).fill('Playwright供应商');

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);

    // 搜索
    await page.locator('input[placeholder="搜索..."]').fill('Playwright');
    await page.waitForTimeout(1000);
  });

  test('09 SCM 仓库管理 — 新建仓库', async ({ page }) => {
    await page.click('text=供应链');
    await page.click('text=仓库管理');
    await page.waitForURL('**/scm/warehouses');

    await page.click('text=新建仓库');
    await page.waitForTimeout(500);

    const inputs = page.locator('form input');
    await inputs.nth(0).fill(`WH-${uid()}`);
    await inputs.nth(1).fill('Playwright仓库');

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);
  });

  test('10 SCM 库存+盘点 — 浏览', async ({ page }) => {
    await page.click('text=供应链');
    await page.click('text=库存管理');
    await page.waitForURL('**/scm/inventory');
    await expect(page.locator('text=库存管理')).toBeVisible();

    // 返回并进入盘点
    await page.goBack();
    await page.click('text=盘点管理');
    await page.waitForURL('**/scm/stocktakes');
    await expect(page.locator('text=盘点管理')).toBeVisible();
  });

  test('11 MGMT 财务 — 新建科目', async ({ page }) => {
    await page.click('text=财务管理');
    await page.click('text=总账科目');
    await page.waitForURL('**/mgmt/finance/accounts');

    await page.click('text=新建科目');
    await page.waitForTimeout(500);

    const inputs = page.locator('form input');
    await inputs.nth(0).fill(`T${uid()}`);
    await inputs.nth(1).fill('Playwright测试科目');

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);
  });

  test('12 MGMT 凭证+AP/AR — 浏览', async ({ page }) => {
    await page.click('text=财务管理');
    await page.click('text=记账凭证');
    await page.waitForURL('**/mgmt/finance/journal');
    await expect(page.locator('text=记账凭证')).toBeVisible();

    await page.goBack();
    await page.click('text=应付');
    await page.waitForURL('**/mgmt/finance/apar');
    await expect(page.locator('text=应付')).toBeVisible();
  });

  test('13 MGMT 人力 — 新建员工', async ({ page }) => {
    await page.click('text=人力资源');
    await page.click('text=员工管理');
    await page.waitForURL('**/mgmt/hr/employees');

    await page.click('text=新建员工');
    await page.waitForTimeout(500);

    const inputs = page.locator('form input');
    await inputs.nth(0).fill(`PW-${uid()}`);
    await inputs.nth(1).fill('Playwright员工');

    await page.click('button:text("保存")');
    await page.waitForTimeout(1000);
  });

  test('14 MGMT KPI 看板 — 浏览', async ({ page }) => {
    await page.click('text=KPI 看板');
    await page.waitForURL('**/mgmt/kpi');
    await expect(page.locator('text=KPI 看板')).toBeVisible();
    // 验证有 KPI 卡片
    await expect(page.locator('text=达成').first()).toBeVisible();
  });

  test('15 MGMT 审批 — 浏览', async ({ page }) => {
    await page.click('text=审批中心');
    await page.click('text=审批记录');
    await page.waitForURL('**/mgmt/approval/list');
    await expect(page.getByRole('heading', { name: '审批中心' })).toBeVisible();
  });

  test('16 导航前进后退', async ({ page }) => {
    // 驾驶舱
    await expect(page.locator('text=领导驾驶舱')).toBeVisible();

    // 进入 PLM
    await page.click('text=产品生命周期');
    await expect(page.locator('text=产品生命周期管理')).toBeVisible();

    // 进入 MFG
    await page.click('text=生产制造');
    await expect(page.locator('text=生产制造管理')).toBeVisible();

    // 后退 → PLM
    await page.goBack();
    await expect(page.locator('text=产品生命周期管理')).toBeVisible();

    // 后退 → 驾驶舱
    await page.goBack();
    await expect(page.locator('text=领导驾驶舱')).toBeVisible();

    // 前进 → PLM
    await page.goForward();
    await expect(page.locator('text=产品生命周期管理')).toBeVisible();
  });
});
