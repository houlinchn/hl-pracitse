export default defineNuxtConfig({
  compatibilityDate: "2025-05-15",
  devtools: { enabled: false },
  css: ["~/assets/main.css"],
  runtimeConfig: { apiBase: "http://127.0.0.1:13081" },
  typescript: { strict: true },
  app: {
    head: {
      title: "Voxnova · 在线英语教师招聘",
      htmlAttrs: { lang: "zh-CN" },
      meta: [
        {
          name: "description",
          content:
            "加入 Voxnova，开启在线英语教学的新可能。在这里填写教师申请、保存草稿、提交资料并查看初筛状态。",
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
