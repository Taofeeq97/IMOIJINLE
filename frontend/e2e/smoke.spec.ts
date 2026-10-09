import { test, expect } from "@playwright/test";

test("public home shows brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Imo Ijinle Academy").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /Learn with calm authority/i })).toBeVisible();
});

test("login page has form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign in/i })).toBeVisible();
});
