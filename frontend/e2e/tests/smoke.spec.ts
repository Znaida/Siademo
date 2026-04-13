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
    const todosLosErrores: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        todosLosErrores.push(text);
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
    await page.waitForTimeout(5000);

    if (erroresCriticos.length > 0) {
      console.log('=== TODOS LOS ERRORES DE CONSOLA ===');
      todosLosErrores.forEach((e, i) => console.log(`[${i+1}] ${e}`));
      console.log('=== ERRORES CRÍTICOS (no filtrados) ===');
      erroresCriticos.forEach((e, i) => console.log(`[${i+1}] ${e}`));
    }

    // No debe haber errores críticos de JavaScript
    expect(erroresCriticos, `Errores críticos encontrados:\n${erroresCriticos.join('\n')}`).toHaveLength(0);
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
