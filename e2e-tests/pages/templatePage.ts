import { Page } from "@playwright/test";
import { JadawelPage, PageConfig } from "./jadawelPage";

export class TemplatePage extends JadawelPage {
  readonly templateSlug: String;

  constructor(pageConfig: PageConfig, slug: String) {
    super(pageConfig);
    this.templateSlug = slug;
  }

  getFullUrl() {
    return `${this.baseUrl}/template/${this.templateSlug}`;
  }
}
