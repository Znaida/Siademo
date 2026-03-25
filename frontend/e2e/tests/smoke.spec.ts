import { test, expect } from '@playwright/test';

/**
 * T6.5.2 — Smoke Tests post-deploy (Opción C)
 * Se ejecutan contra la URL de Azure después de cada deploy.
 * Verifican que la app está viva y los servicios esenciales responden.
 *
 * Variable de entorno: BASE_URL=https://ashy-desert-090fd4a0f.2.azurestaticapps.net
 */

test.describe('Smoke Tests — Azure Deploy', () => {

  test('la aplicación carga y muestra el login', async ({ page }) => {
    // Azure puede tardar en responder - reintentos con waitForFunction
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    // El título SIADE debe estar visible
    await expect(page.locator('h1')).toHaveText('SIADE', { timeout: 30_000 });
  });

  test('el captcha responde desde el backend', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    // El captcha se carga desde /auth/captcha en el backend
    // Si el backend está caído, el captcha no aparece nunca
    await expect(page.locator('.math-question')).toBeVisible({ timeout: 30_000 });
  });

  test('la app no muestra errores críticos de consola', async ({ page }) => {
    const erroresCriticos: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignorar errores de red conocidos que no son bloqueantes
        if (
          !text.includes('favicon') &&
          !text.includes('zone.js') &&
          !text.includes('404') &&
          !text.includes('401') &&
          !text.includes('Failed to load resource') &&
          !text.includes('ERR_') &&
          !text.includes('net::')
        ) {
          erroresCriticos.push(text);
        }
      }
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    // No debe haber errores críticos de JavaScript
    expect(erroresCriticos.length).toBe(0);
  });

  test('la página es responsiva en mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 }); // iPhone SE
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.locator('h1')).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('h1')).toHaveText('SIADE');
  });

  test('la página es responsiva en desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.locator('h1')).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('h1')).toHaveText('SIADE');
  });

});
