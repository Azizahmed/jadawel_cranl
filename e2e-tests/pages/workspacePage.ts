import { Page } from "@playwright/test";
import { JadawelPage, PageConfig } from "./jadawelPage";
import { Sidebar } from "./components/sidebar";
import { Workspace } from "../fixtures/workspace";
import { deleteUser, User } from "../fixtures/user";

export class WorkspacePage extends JadawelPage {
  readonly sidebar: Sidebar;
  readonly workspace: Workspace;
  readonly user: User;

  constructor(pageConfig: PageConfig, user: User, workspace: Workspace) {
    super(pageConfig);
    this.sidebar = new Sidebar(pageConfig.page);
    this.user = user;
    this.workspace = workspace;
  }

  async authenticate() {
    const realtimeReady = this.page.waitForEvent("websocket", {
      predicate: (socket) => socket.url().includes("/ws/core/"),
    });
    await this.page.goto(`${this.baseUrl}?token=${this.user.refreshToken}`);
    return await realtimeReady;
  }

  getFullUrl() {
    return `${this.baseUrl}/workspace/${this.workspace.id}`;
  }

  async removeAll() {
    // We only want to bother cleaning up in a devs local env or when pointed at a real
    // server. If in CI then the first user will be the first admin and this will fail.
    // Secondly in CI we are going to delete the database anyway so no need to clean-up.
    if (!process.env.CI) {
      await deleteUser(this.user);
      // TODO remove workspace
    }
  }
}
