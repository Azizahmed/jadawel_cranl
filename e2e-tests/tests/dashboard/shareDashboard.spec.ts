import { expect, test } from "../jadawelTest";
import { getClient } from "../../client";
import { jadawelConfig } from "../../playwright.config";

test("an owner can create and open a public dashboard link", async ({
  page,
  workspacePage,
}) => {
  const dashboardResponse = await getClient(workspacePage.user).post(
    `applications/workspace/${workspacePage.workspace.id}/`,
    {
      name: "Share regression dashboard",
      type: "dashboard",
    },
  );
  const dashboard = dashboardResponse.data;
  const sharePath = `/api/arabase/dashboard/${dashboard.id}/share/`;
  const expectedBackendOrigin = new URL(jadawelConfig.PUBLIC_BACKEND_URL)
    .origin;
  const shareResponses: any[] = [];
  const malformedApiRequests: string[] = [];

  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname === sharePath) {
      shareResponses.push(response);
    }
  });
  page.on("request", (request) => {
    if (/\/\/api(?:\/|$)/.test(new URL(request.url()).pathname)) {
      malformedApiRequests.push(request.url());
    }
  });

  await page.goto(
    `${jadawelConfig.PUBLIC_WEB_FRONTEND_URL}/dashboard/${dashboard.id}`,
  );
  await expect(
    page.locator(".header__filter-name", { hasText: "Share dashboard" }),
  ).toBeVisible();
  await expect
    .poll(
      () =>
        shareResponses.filter(
          (response) => response.request().method() === "GET",
        ).length,
    )
    .toBe(1);

  const initialGet = shareResponses.find(
    (response) => response.request().method() === "GET",
  );
  if (!initialGet) {
    throw new Error("The dashboard share GET response was not captured");
  }
  expect(new URL(initialGet.url()).origin).toBe(expectedBackendOrigin);
  expect(new URL(initialGet.url()).pathname).toBe(sharePath);
  expect(initialGet.status()).toBe(200);
  expect(initialGet.headers()["content-type"]).toContain("application/json");
  await expect(initialGet.json()).resolves.toBeNull();

  await page
    .locator(".header__filter-link", { hasText: "Share dashboard" })
    .click();
  const createLink = page.getByRole("button", { name: "Create link" });
  await expect(createLink).toBeVisible();

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.evaluate(() => window.dispatchEvent(new Event("resize")));

  await createLink.click();
  await expect
    .poll(
      () =>
        shareResponses.filter(
          (response) => response.request().method() === "POST",
        ).length,
    )
    .toBe(1);

  const postResponse = shareResponses.find(
    (response) => response.request().method() === "POST",
  );
  if (!postResponse) {
    throw new Error("The dashboard share POST response was not captured");
  }
  expect(new URL(postResponse.url()).origin).toBe(expectedBackendOrigin);
  expect(new URL(postResponse.url()).pathname).toBe(sharePath);
  expect(postResponse.status()).toBe(200);
  expect(postResponse.headers()["content-type"]).toContain("application/json");
  const share = await postResponse.json();
  expect(share.slug).toEqual(expect.any(String));
  expect(share.slug).not.toBe("");

  await expect(page.locator(".view-sharing__shared-link-box")).toBeVisible();

  const publicUrl = (
    await page.locator(".view-sharing__shared-link-box").textContent()
  )?.trim();
  if (!publicUrl) {
    throw new Error("The created public dashboard URL was not rendered");
  }
  expect(new URL(publicUrl).pathname).toBe(`/public/dashboard/${share.slug}`);

  const publicResponse = await page.goto(publicUrl);
  expect(publicResponse?.status()).toBe(200);
  await expect(page.locator(".dashboard-app")).toBeVisible();
  expect(
    shareResponses.filter((response) => response.request().method() === "GET"),
  ).toHaveLength(1);
  expect(
    shareResponses.filter((response) => response.request().method() === "POST"),
  ).toHaveLength(1);
  expect(malformedApiRequests).toEqual([]);
});
