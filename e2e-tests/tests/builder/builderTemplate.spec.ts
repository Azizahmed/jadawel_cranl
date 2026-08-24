import { TemplatePage } from "../../pages/templatePage";
import { expect, test } from "../jadawelTest";

test.describe("Builder template application test suite", () => {
  test("Can show a template from the local production catalog", async ({
    page,
    goto,
  }) => {
    const templatePage = new TemplatePage(
      { page, goto },
      "project-management-en",
    );

    await templatePage.goto();

    await expect(page.locator(".tree__link-text")).toHaveText(
      "Project Management",
    );
    await expect(
      page.locator(".tree__sub-link", { hasText: "Team" }),
    ).toBeVisible();
  });
});
