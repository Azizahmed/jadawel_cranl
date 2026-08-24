import { expect, test } from "../jadawelTest";
import { LoginPage } from "../../pages/loginPage";

test.describe("Session lifecycle", () => {
  test("An anonymous visitor is sent to the login page @fast", async ({
    page,
  }) => {
    await page.goto(
      `${process.env.PUBLIC_WEB_FRONTEND_URL || "http://localhost:3000"}/dashboard`,
    );

    await expect(page, "A protected route redirects to login.").toHaveURL(
      /\/login/,
    );
  });

  test("A signed in user can log out again @fast", async ({
    workspacePage,
  }) => {
    await workspacePage.goto();

    await workspacePage.sidebar.logout();

    await expect(
      workspacePage.page,
      "Logging out returns the user to the login page.",
    ).toHaveURL(/\/login/);
  });

  test("The session survives a reload @fast", async ({ workspacePage }) => {
    await workspacePage.goto();
    await workspacePage.page.reload();

    await expect(
      workspacePage.sidebar.workspaceSelector,
      "The user is still signed in after reloading.",
    ).toBeVisible();
  });

  test("An existing account can sign in through the form @fast", async ({
    page,
    goto,
    workspacePage,
  }) => {
    // Log out the fixture account, then exercise the real sign-in form with the
    // same account. It already has a workspace and completed onboarding.
    await workspacePage.goto();
    await workspacePage.sidebar.logout();

    const { email, password } = workspacePage.user;
    if (!password) {
      throw new Error("The fixture user must retain its generated password");
    }
    const loginPage = new LoginPage({ page, goto });

    await loginPage.loginWithPassword(email, password);

    await expect(
      page.locator(".sidebar__workspaces-selector"),
      "The account lands on its own workspace.",
    ).toBeVisible();
  });
});
