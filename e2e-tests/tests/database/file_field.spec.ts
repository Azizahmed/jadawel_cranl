import { expect, test } from "../jadawelTest";
import { TablePage } from "../../pages/database/tablePage";

test.describe("File field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("User can upload an image and download it again @upload", async ({
    page,
    goto,
    workspacePage,
  }) => {
    // Click "Add new" > "From template".
    const templateModal =
      await workspacePage.sidebar.openCreateAppFromTemplateModal();
    await templateModal.waitUntilLoaded();

    const templatesLoadingSpinner = templateModal.getLoadingSpinner();

    await expect(
      templatesLoadingSpinner,
      "Checking that the templates modal spinner is hidden."
    ).toBeHidden();

    await templateModal.clickUseThisTemplateButton();

    await workspacePage.sidebar.selectDatabaseAndTableByName(
      "Project Tracker",
      "Projects"
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.addNewFieldOfType("File");
    const imageWidth =
      await tablePage.uploadImageToFirstFileFieldCellAndGetWidth();

    expect(imageWidth).toBeGreaterThan(0);
    expect(await tablePage.downloadFirstFileFieldImage()).toBe(
      "testuploadimage.png"
    );
  });
});
