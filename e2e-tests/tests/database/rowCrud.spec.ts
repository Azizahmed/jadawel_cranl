import { expect, test } from "../jadawelTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";

/**
 * The grid is where our users spend their day: adding a row, typing in it and
 * removing it again is the journey that has to keep working.
 */
test.describe("Grid row editing", () => {
  test("A user can add a row, fill it and see it after a reload", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "Row CRUD database",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Tasks", database);
    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // A new table starts with two empty rows.
    const rowsBefore = await tablePage.rowsInLeftSection().count();

    await tablePage.clickAddRow();
    await tablePage.fillPrimaryCellOfRow(rowsBefore, "Ship the RTL fixes");

    await page.reload();

    await expect(
      tablePage.primaryCellOfRow(rowsBefore),
      "The typed value was persisted, not only rendered."
    ).toContainText("Ship the RTL fixes");
  });

  test("A user can delete a row again", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "Row delete database",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Tasks", database);
    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    const rowsBefore = await tablePage.rowsInLeftSection().count();
    await tablePage.clickAddRow();
    await tablePage.fillPrimaryCellOfRow(rowsBefore, "Temporary row");

    await tablePage.deleteRow(rowsBefore);

    await expect(
      tablePage.rowsInLeftSection(),
      "The row is gone from the grid."
    ).toHaveCount(rowsBefore);
    await expect(
      page.locator(".grid-view__left"),
      "And its value is gone with it."
    ).not.toContainText("Temporary row");
  });
});
