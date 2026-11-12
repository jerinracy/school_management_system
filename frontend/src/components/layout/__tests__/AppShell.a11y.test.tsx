import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import { AppShell } from "@/components/layout/AppShell";
import i18n from "@/i18n";
import { ThemeProvider } from "@/lib/theme";

describe("AppShell Accessibility & Permissions", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
    await i18n.changeLanguage("en");
  });

  it("defaults to light theme and toggles to dark", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter>
          <AppShell>
            <h1>Overview</h1>
          </AppShell>
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(document.documentElement.classList.contains("dark")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("hides sidebar items when permission is missing", () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <AppShell permissions={["students.view"]}>
            <h1>Overview</h1>
          </AppShell>
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.queryByText("Fees & Accounts")).not.toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(
      <ThemeProvider>
        <MemoryRouter>
          <AppShell>
            <h1>Overview</h1>
          </AppShell>
        </MemoryRouter>
      </ThemeProvider>,
    );

    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
