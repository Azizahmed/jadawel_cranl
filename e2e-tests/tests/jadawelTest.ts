//import { test as base } from "@playwright/test";
import { WorkspacePage } from "../pages/workspacePage";
import { createUser } from "../fixtures/user";
import { BuilderPagePage } from "../pages/builder/builderPagePage";
import { createWorkspace } from "../fixtures/workspace";
import { createBuilderPage } from "../fixtures/builder/builderPage";
import { createBuilder } from "../fixtures/builder/builder";
import { createAutomation } from "../fixtures/automation/automation";
import { createAutomationWorkflow } from "../fixtures/automation/automationWorkflow";
import { AutomationWorkflowPage } from "../pages/automation/automationWorkflowPage";
import { expect, test as base } from "@nuxt/test-utils/playwright";

// Declare the types of your fixtures.
type JadawelFixtures = {
  workspacePage: WorkspacePage;
  builderPagePage: BuilderPagePage;
  automationWorkflowPage: AutomationWorkflowPage;
};

type ExpectedHttpError = {
  status: number;
  urlIncludes: string;
};

type JadawelOptions = {
  expectedHttpErrors: ExpectedHttpError[];
};

export function monitorBrowserErrors(
  page,
  expectedHttpErrors: ExpectedHttpError[] = []
) {
  const browserErrors: string[] = [];
  const browserWarnings: string[] = [];

  const onConsole = (message) => {
    if (message.type() === "error") {
      const source = message.location().url;
      // Firefox reports NS_BINDING_ABORTED as a font download error when a route
      // changes while its previous document is still loading. The asset itself is
      // healthy; this is a cancelled request, not a failed application resource.
      const isFirefoxNavigationAbort =
        message.text().includes("downloadable font: download failed") &&
        message.text().includes("status=2152398850");
      if (isFirefoxNavigationAbort) {
        return;
      }
      const isExpectedHttpError = expectedHttpErrors.some(
        ({ status, urlIncludes }) =>
          source.includes(urlIncludes) &&
          message.text().includes(`status of ${status}`)
      );
      if (isExpectedHttpError) {
        return;
      }
      browserErrors.push(
        `console: ${message.text()}${source ? ` (${source})` : ""}`
      );
    } else if (message.type() === "warning") {
      browserWarnings.push(`console warning: ${message.text()}`);
    }
  };
  const onPageError = (error) => {
    browserErrors.push(`pageerror: ${error.stack || error.message}`);
  };
  const onResponse = (response) => {
    if (response.status() >= 500) {
      browserErrors.push(`HTTP ${response.status()}: ${response.url()}`);
    }
  };

  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);

  return () => {
    page.off("console", onConsole);
    page.off("pageerror", onPageError);
    page.off("response", onResponse);
    const diagnostics =
      browserErrors.length > 0
        ? [...browserErrors, ...browserWarnings]
        : browserErrors;
    expect(diagnostics, "Browser console, runtime, or HTTP 5xx errors").toEqual(
      []
    );
  };
}

/**
 * Fixture for all tests that need an authenticated user with an empty workspace.
 */
export const test = base.extend<JadawelFixtures & JadawelOptions>({
  expectedHttpErrors: [[], { option: true }],
  page: async ({ page, expectedHttpErrors }, use) => {
    const verifyBrowserErrors = monitorBrowserErrors(page, expectedHttpErrors);

    await use(page);

    verifyBrowserErrors();
  },
  workspacePage: async ({ page, goto }, use) => {
    // Don't show the cookie notice
    await page.context().addCookies([
      {
        name: "jadawel_dashboard_alert_closed_v2",
        value: "true",
        domain: "localhost",
        path: "/",
      },
    ]);

    const user = await createUser();
    const workspace = await createWorkspace(user);
    const workspacePage = new WorkspacePage({ page, goto }, user, workspace);
    await workspacePage.authenticate();

    await page.evaluate(() => {
      // Prevent the AI panel to automatically open in all tests
      localStorage.setItem("jadawel.rightSidebarOpen", "false");
    });

    // Use the fixture value in the test.
    await use(workspacePage);

    // Clean up the fixture.
    await workspacePage.removeAll();
  },
  builderPagePage: async ({ page, workspacePage, goto }, use) => {
    const builder = await createBuilder(
      "Test builder",
      workspacePage.workspace
    );
    const builderPage = await createBuilderPage(
      "Default page",
      "/default/page",
      builder
    );
    const builderPagePage = new BuilderPagePage(
      { page, goto },
      builder,
      builderPage
    );

    await use(builderPagePage);

    await builderPagePage.removeAll();
  },
  automationWorkflowPage: async ({ page, workspacePage, goto }, use) => {
    const automation = await createAutomation(
      "Test automation",
      workspacePage.workspace
    );
    const automationWorkflow = await createAutomationWorkflow(
      "Default workflow",
      automation
    );
    const automationWorkflowPage = new AutomationWorkflowPage(
      { page, goto },
      automation,
      automationWorkflow
    );

    await use(automationWorkflowPage);
  },
});
export { expect } from "@nuxt/test-utils/playwright";
