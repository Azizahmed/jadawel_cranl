import { expect, test } from "../jadawelTest";
import { LoginPage } from "../../pages/loginPage";
import { createUser, deleteUser, User } from "../../fixtures/user";

let user: User;

test.beforeEach(async () => {
  user = await createUser();
});

test.afterEach(async () => {
  // Only clean up outside of CI: there the first user is the instance admin and
  // the database is thrown away afterwards anyway.
  if (!process.env.CI) {
    await deleteUser(user);
  }
});

test.describe("Sign in failures", () => {
  test.use({
    expectedHttpErrors: [
      { status: 401, urlIncludes: "/api/user/token-auth/" },
    ],
  });

  test("A wrong password keeps the user on the login page @fast", async ({
    page,
    goto,
  }) => {
    const loginPage = new LoginPage({ page, goto });
    await loginPage.goto();

    await loginPage.loginExpectingFailure(user.email, "definitely-not-my-password");

    await expect(
      loginPage.errorAlert,
      "The incorrect credentials error is shown."
    ).toContainText("Incorrect credentials");
    await loginPage.expectOnLoginPage();
  });

  test("An unknown email address is rejected @fast", async ({ page, goto }) => {
    const loginPage = new LoginPage({ page, goto });
    await loginPage.goto();

    await loginPage.loginExpectingFailure(
      `no-such-user-${Date.now()}@jadawel.site`,
      "test1234"
    );

    await loginPage.expectOnLoginPage();
  });

  test("Signing in after a failed attempt still works @fast", async ({
    page,
    goto,
  }) => {
    const loginPage = new LoginPage({ page, goto });
    await loginPage.goto();

    await loginPage.loginExpectingFailure(user.email, "wrong-password");
    await loginPage.loginWithPassword(user.email, user.password || "");

    await expect(
      page.locator(".sidebar__workspaces-selector"),
      "The user lands in the app after correcting the password."
    ).toBeVisible();
  });
});
