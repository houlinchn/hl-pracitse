export default defineNuxtConfig({
  compatibilityDate: "2025-05-15",
  devtools: { enabled: false },
  css: ["~/assets/main.css"],
  runtimeConfig: { apiBase: "http://127.0.0.1:13081" },
  typescript: { strict: true },
  app: {
    head: {
      title: "Teacher Operations · 招聘工作台",
      htmlAttrs: { lang: "zh-CN" },
      meta: [
        {
          name: "description",
          content: "核心招聘流程演示：申请、提交与初筛。仅使用演示数据。",
        },
      ],
    },
  },
  routeRules: {
    "/**": {
      headers: {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Cache-Control": "no-store",
      },
    },
  },
});
