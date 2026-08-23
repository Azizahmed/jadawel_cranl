import { Locator, Page } from "@playwright/test";

/**
 * The "My settings" modal, reachable from the workspace selector in the
 * sidebar.
 */
export class SettingsModal {
  readonly page: Page;
  readonly root: Locator;
  readonly languageDropdown: Locator;
  readonly saveButton: Locator;
  readonly successAlert: Locator;

  constructor(page: Page) {
    this.page = page;
    this.root = page.locator(".modal__box--with-sidebar");
    this.languageDropdown = this.root.locator(".dropdown").first();
    this.saveButton = this.root.locator("form button").last();
    this.successAlert = this.root.locator(".alert--success");
  }

  async waitUntilLoaded() {
    await this.root.waitFor();
  }

  /**
   * Picks an interface language by its native name, e.g. "العربية" or
   * "English", and saves the account.
   */
  async setInterfaceLanguage(name: string) {
    await this.languageDropdown.click();
    await this.languageDropdown.locator(".select__item").getByText(name).click();
    await this.saveButton.click();
    await this.successAlert.waitFor();
  }
}
