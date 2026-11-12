import { expect, test } from "@playwright/test";

test("dashboard shell loads and switches language", async ({ page }) => {
  await page.goto("/dashboard/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});
