import { expect, test } from "../jadawelTest";
import { LoginPage } from "../../pages/loginPage";
import { existingUserCredentials } from "../../fixtures/user";

test.describe("Session lifecycle", () => {
  test("An anonymous visitor is sent to the login page @fast", async ({
    page,
  }) => {
    await page.goto(`${process.env.PUBLIC_WEB_FRONTEND_URL || "http://localhost:3000"}/dashboard`);

    await expect(page, "A protected route redirects to login.").toHaveURL(
      /\/login/
    );
  });

  test("A signed in user can log out again @fast", async ({
    workspacePage,
  }) => {
    await workspacePage.goto();

    await workspacePage.sidebar.logout();

    await expect(
      workspacePage.page,
      "Logging out returns the user to the login page."
    ).toHaveURL(/\/login/);
  });

  test("The session survives a reload @fast", async ({ workspacePage }) => {
    await workspacePage.goto();
    await workspacePage.page.reload();

    await expect(
      workspacePage.sidebar.workspaceSelector,
      "The user is still signed in after reloading."
    ).toBeVisible();
  });

  test("An existing account can sign in through the form @fast", async ({
    page,
    goto,
  }) => {
    // Exercises the real sign-in form with an account that already exists on
    // the instance, rather than the token short-circuit the fixtures use.
    const { email, password } = existingUserCredentials();
    const loginPage = new LoginPage({ page, goto });
    await loginPage.goto();

    await loginPage.loginWithPassword(email, password);

    await expect(
      page.locator(".sidebar__workspaces-selector"),
      "The account lands on its own workspace."
    ).toBeVisible();
  });
});
