import { expect, test } from "../jadawelTest";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";

/**
 * The protected endpoint wizard is a security boundary as well as a settings
 * form. Exercise the real page so keyboard focus, lazy metadata loading,
 * review confirmation, and the persisted policy are covered together.
 */
test.describe("MCP protected field settings", () => {
  test("creates a policy through the keyboard-accessible review flow", async ({
    page,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "MCP protected fields",
      workspacePage.workspace,
    );
    const table = await createTable(workspacePage.user, "People", database);

    // The table fixture creates a primary text field, which is enough to prove
    // the lazy field path without relying on generated/private values.
    await page.reload();
    await workspacePage.sidebar.openMySettings();

    const modal = page.locator(".modal__box--with-sidebar");
    await modal.waitFor();
    await modal
      .locator(".modal-sidebar__nav-link")
      .filter({ hasText: /MCP/i })
      .click();
    await modal.getByRole("button", { name: /create endpoint/i }).click();
    await modal
      .locator('[data-test-id="endpoint-name"]')
      .fill("Protected assistant");
    await modal
      .locator('[data-test-id="workspace-id"]')
      .selectOption(String(workspacePage.workspace.id));
    await modal.locator('[data-test-id="next-details"]').click();

    const tableToggle = modal.locator(
      `[data-test-id="expand-table-${table.id}"]`,
    );
    await tableToggle.focus();
    await expect(tableToggle).toBeFocused();
    await page.keyboard.press("Enter");

    const field = modal
      .locator('input[type="checkbox"][data-test-id^="protected-field-"]')
      .first();
    await field.waitFor();
    await field.focus();
    await expect(field).toBeFocused();
    await page.keyboard.press("Space");
    await expect(field).toBeChecked();

    await modal.locator('[data-test-id="next-fields"]').click();
    await expect(modal.locator(".mcp-protection-review")).toContainText(
      "People",
    );
    await modal.locator('[data-test-id="create-protected-endpoint"]').click();

    await expect(
      modal.locator(".mcp-protected-endpoint-settings__item"),
    ).toContainText("Protected assistant");
    await expect(
      modal.locator(".mcp-protected-endpoint-settings__status"),
    ).toContainText(/1/);

    const dimensions = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      documentHeight: document.documentElement.scrollHeight,
      viewportHeight: window.innerHeight,
    }));
    expect(dimensions.documentWidth).toBeLessThanOrEqual(
      dimensions.viewportWidth,
    );
    expect(dimensions.documentHeight).toBeGreaterThan(0);
  });
});
