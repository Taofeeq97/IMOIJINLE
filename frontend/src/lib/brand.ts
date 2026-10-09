import type { BrandSettings } from "@/lib/api/schema";

let cachedBrand: BrandSettings | null = null;

/** Apply brand colors without fighting dark-mode surface tokens. */
export function applyBrandSettings(brand: BrandSettings) {
  if (typeof document === "undefined") return;
  cachedBrand = brand;
  const root = document.documentElement;
  const isDark = root.classList.contains("dark");

  // Accent colors stay brandable in both themes.
  root.style.setProperty("--primary", brand.primary_color);
  root.style.setProperty("--accent", brand.accent_color);
  root.style.setProperty("--ring", brand.primary_color);

  if (isDark) {
    // Dark mode uses CSS `.dark` surface tokens — clear any light brand overrides.
    root.style.removeProperty("--background");
    root.style.removeProperty("--foreground");
    root.style.removeProperty("--ink");
    root.style.removeProperty("--ink-2");
    root.style.removeProperty("--ink-foreground");
    // Soften primary for dark UI (brand greens are often too deep for dark text/links)
    root.style.setProperty("--primary", "#5ec4ab");
    root.style.setProperty("--primary-foreground", "#07211a");
    root.style.setProperty("--ring", "#5ec4ab");
    root.style.setProperty("--accent", brand.accent_color || "#e2b462");
  } else {
    root.style.setProperty("--background", brand.background_color);
    root.style.setProperty("--foreground", brand.foreground_color);
    root.style.setProperty("--ink", brand.ink_color);
    root.style.setProperty("--ink-2", brand.ink2_color);
    root.style.setProperty("--ink-foreground", brand.ink_foreground);
    root.style.setProperty("--primary-foreground", "#ffffff");
  }

  if (brand.extra_css_vars) {
    for (const [key, value] of Object.entries(brand.extra_css_vars)) {
      // Never let extras pin light surfaces over dark theme
      if (isDark && ["background", "foreground", "ink", "ink-2", "ink-foreground"].some((k) => key.includes(k))) {
        continue;
      }
      root.style.setProperty(key.startsWith("--") ? key : `--${key}`, value);
    }
  }
}

export function reapplyBrandForTheme() {
  if (cachedBrand) applyBrandSettings(cachedBrand);
}
