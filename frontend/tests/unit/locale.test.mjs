import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import * as vue from "vue";
import { renderToString } from "vue/server-renderer";
import { compileScript, compileTemplate, parse } from "vue/compiler-sfc";
import ts from "typescript";
import {
  messages,
  translate,
  restoreLocale,
  rememberLocale,
  languageStorageKey,
  effectiveLocale,
  localizedError,
  localizedReason,
  localizedStatuses,
  localizedTime,
} from "../../utils/locale.ts";

// Execute the actual composable and page controller with Vue's in-memory renderer.
// No browser, DOM emulator, network, credentials or database is involved.
Object.assign(globalThis, vue);
let states;
let head;
let fetcher;
Object.assign(globalThis, {
  useState: (key, initial) => {
    if (!states.has(key)) states.set(key, vue.ref(initial()));
    return states.get(key);
  },
  useHead: (value) => {
    head = vue.computed(value);
  },
  $fetch: (...args) => fetcher(...args),
  window: { localStorage: storage() },
});

function storage(initial) {
  const values = new Map(
    initial === undefined ? [] : [[languageStorageKey, initial]],
  );
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}
async function moduleFrom(source) {
  const rewritten = source.replaceAll(
    '"~/utils/locale"',
    JSON.stringify(new URL("../../utils/locale.ts", import.meta.url).href),
  );
  const code = ts.transpileModule(rewritten, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
    },
  }).outputText;
  // Bare imports in data URLs cannot resolve packages: use absolute package URLs.
  const resolved = code.replace(
    /from ["'](vue(?:\/server-renderer)?)["']/g,
    (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`,
  );
  return import(
    `data:text/javascript;base64,${Buffer.from(resolved).toString("base64")}`
  );
}
const { useLocale } = await moduleFrom(
  readFileSync(
    new URL("../../composables/useLocale.ts", import.meta.url),
    "utf8",
  ),
);
Object.assign(globalThis, { useLocale });
function component(file, inlineTemplate = false) {
  const source = readFileSync(new URL(file, import.meta.url), "utf8");
  const { descriptor, errors } = parse(source);
  assert.deepEqual(errors, []);
  const template = compileTemplate({
    source: descriptor.template.content,
    filename: file,
    id: file,
  });
  assert.deepEqual(template.errors, []);
  return moduleFrom(
    compileScript(descriptor, { id: file, inlineTemplate }).content,
  );
}
const page = (await component("../../pages/index.vue")).default;
const home = (await component("../../components/RecruitmentHome.vue", true))
  .default;
const renderer = vue.createRenderer({
  createComment: () => ({}),
  insert() {},
  remove() {},
  parentNode() {},
  nextSibling() {},
});
const pageDescriptor = parse(
  readFileSync(new URL("../../pages/index.vue", import.meta.url), "utf8"),
).descriptor;
const pageScript = compileScript(pageDescriptor, { id: "page-ssr" });
const pageTemplate = compileTemplate({
  source: pageDescriptor.template.content,
  filename: "index.vue",
  id: "page-ssr",
  ssr: true,
  ssrCssVars: [],
  compilerOptions: { bindingMetadata: pageScript.bindings },
});
assert.deepEqual(pageTemplate.errors, []);
const { ssrRender } = await moduleFrom(pageTemplate.code);
async function renderPage(vm, overrides = {}) {
  const app = vue.createSSRApp({
    setup: () => ({ ...vm, ...overrides }),
    ssrRender,
  });
  app.component("RecruitmentHome", home);
  return renderToString(app);
}
const flush = async () => {
  for (let i = 0; i < 10; i++) {
    await Promise.resolve();
    await vue.nextTick();
  }
};
async function mount(role = "applicant", preference = "en") {
  states = new Map();
  window.localStorage = storage(preference);
  const calls = [];
  let account = {
    id: "synthetic",
    email: "synthetic@example.com",
    role,
    permissions: role === "staff" ? ["applications.read"] : [],
  };
  const item = {
    id: "application",
    name: "原始 Name",
    contact_email: "synthetic@example.com",
    statement: "Untranslated 申请说明",
    status: "draft",
    version: 1,
    events: [],
  };
  fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url === "/api/auth/me" || url === "/api/auth/login") return account;
    if (url.endsWith("/logout")) return;
    if (url === "/api/applications" || url === "/api/staff/applications") {
      return options?.method ? { ...item, ...options.body } : [{ ...item }];
    }
    if (options?.method === "PATCH")
      return { ...item, ...options.body, version: 2 };
    if (url.endsWith("/submit"))
      return { ...item, status: "submitted", version: 3 };
    return { ...item };
  };
  const app = renderer.createApp({ ...page, render: () => null });
  const vm = app.mount({}).$.setupState;
  await flush();
  return {
    app,
    vm,
    calls,
    item,
    setAccount: (value) => {
      account = value;
    },
  };
}

test("catalog contains a nonempty matching pair for every phrase", () => {
  for (const [key, pair] of Object.entries(messages)) {
    assert.deepEqual(Object.keys(pair).sort(), ["en", "zh"]);
    assert.ok(pair.en.trim(), key);
    assert.ok(pair.zh.trim(), key);
    assert.equal(translate(key, "en"), pair.en);
    assert.equal(translate(key, "zh"), pair.zh);
  }
});
test("language storage validates values and tolerates unavailable storage", () => {
  for (const value of [
    undefined,
    "",
    "fr",
    "EN",
    "__proto__",
    '{"role":"staff"}',
  ]) {
    assert.equal(restoreLocale(storage(value)), "zh");
  }
  const store = storage();
  assert.equal(rememberLocale(store, "en"), "en");
  assert.equal(restoreLocale(store), "en");
  assert.equal(rememberLocale(store, "staff"), "zh");
  const blocked = {
    getItem() {
      throw Error();
    },
    setItem() {
      throw Error();
    },
  };
  assert.equal(restoreLocale(blocked), "zh");
  assert.equal(rememberLocale(blocked, "en"), "en");
  assert.equal(effectiveLocale("en", true), "zh");
});
test("all API errors, validation fields, statuses and dates are localized safely", () => {
  const backend = ["main.py", "accounts.py", "applications.py"]
    .map((file) =>
      readFileSync(
        new URL(`../../../backend/poc/${file}`, import.meta.url),
        "utf8",
      ),
    )
    .join("\n");
  const details = [
    ...backend.matchAll(/raise HTTPException\(\d+, "([^"]+)"\)/g),
  ].map((match) => match[1]);
  for (const detail of details) {
    // Delegation-only errors are internal Chinese and outside applicant translation.
    if (
      detail.includes("委托权限") ||
      detail.includes("委托范围") ||
      detail === "仅员工可管理委托" ||
      detail === "委托不存在"
    )
      continue;
    assert.ok(messages[detail], detail);
    assert.equal(
      localizedError({ data: { detail } }, "en"),
      messages[detail].en,
    );
  }
  const invalid = {
    data: {
      detail: "输入不符合要求，请检查字段长度、格式及必填项",
      fields: [
        "name",
        "contact_email",
        "statement",
        "password",
        "expected_version",
        "<private>",
      ],
    },
  };
  assert.match(
    localizedError(invalid, "en"),
    /Name, Contact email, Application statement, Password, Version, Field/,
  );
  assert.match(
    localizedError(invalid, "zh"),
    /姓名、联系邮箱、申请说明、密码、版本、字段/,
  );
  for (const error of [
    null,
    {},
    { data: { detail: "<private upstream error>", fields: ["secret"] } },
    { data: { detail: ["private"] } },
  ]) {
    assert.equal(
      localizedError(error, "en"),
      messages["服务暂时不可用，请稍后重试"].en,
    );
  }
  assert.deepEqual(localizedStatuses("en"), {
    draft: "Draft",
    submitted: "Submitted",
    screening: "Screening",
  });
  assert.deepEqual(localizedStatuses("zh"), {
    draft: "草稿",
    submitted: "已提交",
    screening: "初筛",
  });
  assert.equal(localizedTime("invalid", "en"), "—");
  assert.notEqual(
    localizedTime("2026-11-12T10:00:00Z", "en"),
    localizedTime("2026-11-12T10:00:00Z", "zh"),
  );
});
test("system event reasons are translated without translating staff prose or changing records", () => {
  const event = {
    before: null,
    after: "draft",
    channel: "web",
    reason: "创建草稿",
  };
  assert.equal(localizedReason(event, "en"), "Draft created");
  assert.equal(event.reason, "创建草稿");
  assert.equal(
    localizedReason(
      {
        ...event,
        before: "draft",
        after: "submitted",
        reason: "申请人提交申请",
      },
      "en",
    ),
    "Application submitted by applicant",
  );
  for (const channel of ["web", "ai"]) {
    assert.equal(
      localizedReason(
        { ...event, before: "submitted", after: "screening", channel },
        "en",
      ),
      "创建草稿",
    );
  }
});
test("actual home renders both languages with no closing section and remaining application entry", async () => {
  for (const locale of ["zh", "en"]) {
    states = new Map([["applicant-language", vue.ref(locale)]]);
    const html = await renderToString(vue.createSSRApp(home));
    assert.ok(html.includes(messages["开始申请"][locale]));
    assert.ok(html.includes(messages["资料没写完，可以下次继续吗？"][locale]));
    assert.ok(html.includes(messages["回到顶部 ↑"][locale]));
    assert.ok(!html.includes('class="closing"'));
    assert.ok(!html.includes("THE NEXT CHAPTER IS YOURS"));
    if (locale === "en") assert.ok(!/[\u3400-\u9fff]/u.test(html));
  }
});
test("actual applicant controller restores language, preserves unsaved fields and does not write on switching", async () => {
  const { app, vm, calls, item } = await mount();
  assert.equal(vm.locale, "en");
  assert.equal(head.value.htmlAttrs.lang, "en");
  assert.equal(head.value.title, messages["Voxnova · 在线英语教师招聘"].en);
  vm.draft.name = "Unsaved 未保存";
  vm.draft.statement = "Unsaved teaching experience";
  const selected = vm.selected;
  const count = calls.length;
  vm.setLocale("zh");
  await flush();
  assert.equal(head.value.htmlAttrs.lang, "zh-CN");
  assert.equal(vm.draft.name, "Unsaved 未保存");
  assert.equal(vm.selected, selected);
  assert.equal(calls.length, count);
  vm.setLocale("en");
  await vm.saveDraft();
  const patch = calls.find((call) => call.options?.method === "PATCH");
  assert.deepEqual(patch.options.body, {
    name: "Unsaved 未保存",
    contact_email: item.contact_email,
    statement: "Unsaved teaching experience",
    expected_version: 1,
  });
  assert.equal(
    vm.t(vm.notice),
    messages["草稿已保存。你可以继续编辑，或确认后提交。"].en,
  );
  vm.setLocale("zh");
  assert.equal(
    vm.t(vm.notice),
    messages["草稿已保存。你可以继续编辑，或确认后提交。"].zh,
  );
  await vm.submitApplication();
  assert.equal(vm.selected.status, "submitted");
  app.unmount();
});
test("actual applicant and authentication templates render complete English copy", async () => {
  const { app, vm, item, calls } = await mount();
  const assertEnglish = (html) => {
    const withoutUserContent = html
      .replaceAll("中文", "")
      .replaceAll(item.name, "")
      .replaceAll(item.statement, "");
    assert.ok(!/[\u3400-\u9fff]/u.test(withoutUserContent));
  };
  assertEnglish(await renderPage(vm));
  assertEnglish(
    await renderPage(vm, {
      selected: {
        ...item,
        status: "submitted",
        events: [
          {
            id: "event",
            before: "draft",
            after: "submitted",
            channel: "web",
            reason: "申请人提交申请",
            at: "2026-11-12T10:00:00Z",
          },
        ],
      },
    }),
  );
  for (const authMode of ["login", "register"]) {
    const html = await renderPage(vm, {
      account: null,
      authOpen: true,
      authMode,
    });
    assertEnglish(html);
    assert.ok(html.includes(messages["邮箱"].en));
    assert.ok(html.includes(messages["密码"].en));
    assert.ok(html.includes('class="language-switch auth-language-switch"'));
  }
  vm.email = "unsaved@example.com";
  vm.password = "unsaved-synthetic-password";
  const count = calls.length;
  vm.setLocale("zh");
  assert.equal(vm.email, "unsaved@example.com");
  assert.equal(vm.password, "unsaved-synthetic-password");
  assert.equal(calls.length, count);
  app.unmount();
});
test("errors retranslate after a switch, including unauthorized session expiry", async () => {
  const { app, vm } = await mount();
  fetcher = async () => {
    throw {
      status: 422,
      data: {
        detail: "输入不符合要求，请检查字段长度、格式及必填项",
        fields: ["name"],
      },
    };
  };
  await vm.saveDraft();
  assert.match(vm.displayError, /Name/);
  vm.setLocale("zh");
  assert.match(vm.displayError, /姓名/);
  vm.setLocale("en");
  fetcher = async () => {
    throw { status: 401, data: { detail: "登录或委托已失效，请重新认证" } };
  };
  await vm.refresh();
  assert.equal(vm.account, null);
  assert.equal(vm.locale, "en");
  assert.equal(vm.displayError, messages["登录或委托已失效，请重新认证"].en);
  app.unmount();
});
test("staff stays Chinese after English login, while external preference survives logout", async () => {
  const { app, vm, calls } = await mount("staff", "en");
  assert.equal(vm.locale, "zh");
  assert.equal(head.value.htmlAttrs.lang, "zh-CN");
  assert.equal(vm.t("退出登录"), "退出登录");
  vm.setLocale("en");
  assert.equal(vm.locale, "zh");
  assert.equal(restoreLocale(window.localStorage), "en");
  assert.equal(calls[1].url, "/api/staff/applications");
  await vm.logout();
  assert.equal(vm.locale, "en");
  vm.email = "staff@example.com";
  vm.password = "synthetic-password";
  await vm.authenticate();
  assert.equal(vm.locale, "zh");
  const login = calls.find((call) => call.url === "/api/auth/login");
  assert.deepEqual(login.options.body, {
    email: "staff@example.com",
    password: "synthetic-password",
  });
  app.unmount();
});
