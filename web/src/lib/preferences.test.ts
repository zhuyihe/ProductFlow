import { describe, expect, it } from "vitest";

import { DEFAULT_LOCALE, enUS, interpolate, jaJP, resolveLocale, translate, zhCN } from "./i18n";
import { resolveTheme, resolveThemePreference } from "./theme";

describe("i18n helpers", () => {
  it("resolves supported locales and falls back to Chinese", () => {
    expect(resolveLocale("en-US")).toBe("en-US");
    expect(resolveLocale("zh-CN")).toBe("zh-CN");
    expect(resolveLocale("fr-FR")).toBe(DEFAULT_LOCALE);
    expect(resolveLocale(null)).toBe(DEFAULT_LOCALE);
  });

  it("translates keys with interpolation", () => {
    expect(translate("zh-CN", "products.paginationSummary", { page: 2, totalPages: 5, total: 48 })).toBe(
      "第 2 / 5 页 · 共 48 个商品",
    );
    expect(translate("en-US", "products.paginationSummary", { page: 2, totalPages: 5, total: 48 })).toBe(
      "Page 2 / 5 · 48 products",
    );
    expect(interpolate("Hello {name}, {missing}", { name: "Ada" })).toBe("Hello Ada, {missing}");
  });

  it("keeps auth login copy aligned with the real session contract", () => {
    expect(Object.prototype.hasOwnProperty.call(zhCN, "auth.login.scope.quota")).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(enUS, "auth.login.scope.quota")).toBe(false);
    expect(Object.prototype.hasOwnProperty.call(jaJP, "auth.login.scope.quota")).toBe(false);
    expect(translate("zh-CN", "auth.login.sessionTtl")).not.toContain("14 天");
    expect(translate("en-US", "auth.login.sessionTtl")).not.toContain("14 days");
  });
});

describe("theme helpers", () => {
  it("resolves persisted theme preference values", () => {
    expect(resolveThemePreference("dark")).toBe("dark");
    expect(resolveThemePreference("light")).toBe("light");
    expect(resolveThemePreference("system")).toBe("system");
    expect(resolveThemePreference("sepia")).toBe("system");
  });

  it("resolves system mode from prefers-color-scheme", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });
});

