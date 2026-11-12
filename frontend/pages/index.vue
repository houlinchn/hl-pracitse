<script setup lang="ts">
import type {
  Account,
  Application,
  Audit,
  Delegation,
  Status,
  StatusEvent,
} from "~/composables/usePortal";

import {
  localizedStatuses,
  localizedTime,
  localizedError,
  localizedReason,
  type MessageKey,
} from "~/utils/locale";

const account = ref<Account | null>(null);
const loading = ref(true);
const busy = ref(false);
const error = ref<unknown>(null);
const notice = ref<MessageKey | "">("");
const authMode = ref<"login" | "register">("login");
const authOpen = ref(false);
const email = ref("");
const password = ref("");
const section = ref<"applications" | "delegations">("applications");
const applications = ref<Application[]>([]);
const selected = ref<Application | null>(null);
const filter = ref("");
const offset = ref(0);
const reason = ref("");
const audits = ref<Audit[] | null>(null);
const draft = reactive({ name: "", contact_email: "", statement: "" });
const delegations = ref<Delegation[]>([]);
const grantPermissions = ref<string[]>([]);
const grantScope = ref<"current" | "all">("current");
const issuedToken = ref("");
const issuedId = ref("");
const isStaff = computed(() => account.value?.role === "staff");
const { locale, t, setLocale } = useLocale(isStaff);
const statusLabel = computed(() => localizedStatuses(locale.value));
const formatTime = (value: string) => localizedTime(value, locale.value);
const displayError = computed(() => localizedError(error.value, locale.value));
const eventReason = (event: StatusEvent) =>
  localizedReason(event, locale.value);
useHead(() => ({
  title: isStaff.value
    ? "Voxnova · 招聘工作台"
    : t("Voxnova · 在线英语教师招聘"),
  htmlAttrs: { lang: locale.value === "en" ? "en" : "zh-CN" },
  meta: [
    {
      name: "description",
      content: t(
        "加入 Voxnova，开启在线英语教学的新可能。在这里填写教师申请、保存草稿、提交资料并查看初筛状态。",
      ),
    },
  ],
}));
const can = (permission: string) =>
  !!account.value?.permissions.includes(permission);
const counts = computed(() => ({
  submitted: applications.value.filter((a) => a.status === "submitted").length,
  screening: applications.value.filter((a) => a.status === "screening").length,
}));
const endpoint = computed(() =>
  isStaff.value ? "/api/staff/applications" : "/api/applications",
);

const authDialog = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
watch(authOpen, async (opened) => {
  if (opened) {
    previousFocus = document.activeElement as HTMLElement | null;
    await nextTick();
    authDialog.value?.querySelector<HTMLInputElement>("#auth-email")?.focus();
  } else {
    password.value = "";
    await nextTick();
    previousFocus?.focus();
  }
});
function openAuth(mode: "login" | "register") {
  authMode.value = mode;
  error.value = "";
  authOpen.value = true;
}
function trapAuthFocus(event: KeyboardEvent) {
  const nodes = authDialog.value?.querySelectorAll<HTMLElement>(
    "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)",
  );
  if (!nodes?.length) return;
  const first = nodes[0]!;
  const last = nodes[nodes.length - 1]!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  }
  if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function clearAccount() {
  account.value = null;
  applications.value = [];
  selected.value = null;
  audits.value = null;
  issuedToken.value = "";
  issuedId.value = "";
  delegations.value = [];
  grantPermissions.value = [];
  section.value = "applications";
  password.value = "";
  email.value = "";
  reason.value = "";
  filter.value = "";
  offset.value = 0;
  Object.assign(draft, { name: "", contact_email: "", statement: "" });
}

async function perform(
  task: () => Promise<void>,
  success: MessageKey | "" = "",
) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await task();
    if (success) notice.value = success;
  } catch (e) {
    error.value = e;
    if ((e as { status?: number }).status === 401 && account.value)
      clearAccount();
  } finally {
    busy.value = false;
  }
}
async function loadApplications() {
  if (isStaff.value && !can("applications.read")) {
    applications.value = [];
    return;
  }
  applications.value = await $fetch<Application[]>(endpoint.value, {
    query: isStaff.value
      ? { status: filter.value || undefined, offset: offset.value, limit: 50 }
      : {},
  });
}
async function openApplication(item: Application) {
  await perform(async () => {
    selected.value = await $fetch<Application>(`${endpoint.value}/${item.id}`);
    audits.value = null;
    reason.value = "";
    Object.assign(draft, {
      name: selected.value.name,
      contact_email: selected.value.contact_email,
      statement: selected.value.statement,
    });
  });
}
async function authenticate() {
  await perform(async () => {
    account.value = await $fetch<Account>(`/api/auth/${authMode.value}`, {
      method: "POST",
      body: { email: email.value, password: password.value },
    });
    password.value = "";
    authOpen.value = false;
    selected.value = null;
    offset.value = 0;
    draft.contact_email = account.value.email;
    await loadApplications();
    if (!isStaff.value && applications.value[0]) {
      selected.value = await $fetch<Application>(
        `${endpoint.value}/${applications.value[0].id}`,
      );
      Object.assign(draft, {
        name: selected.value.name,
        contact_email: selected.value.contact_email,
        statement: selected.value.statement,
      });
    }
  });
}
async function logout() {
  await perform(async () => {
    await $fetch("/api/auth/logout", { method: "POST" });
    clearAccount();
  });
}
async function saveDraft() {
  await perform(async () => {
    const item = selected.value;
    selected.value = await $fetch<Application>(
      item ? `/api/applications/${item.id}` : "/api/applications",
      {
        method: item ? "PATCH" : "POST",
        body: { ...draft, ...(item ? { expected_version: item.version } : {}) },
      },
    );
    Object.assign(draft, {
      name: selected.value.name,
      contact_email: selected.value.contact_email,
      statement: selected.value.statement,
    });
    await loadApplications();
  }, "草稿已保存。你可以继续编辑，或确认后提交。");
}
async function submitApplication() {
  await perform(async () => {
    if (!selected.value) return;
    selected.value = await $fetch<Application>(
      `/api/applications/${selected.value.id}/submit`,
      { method: "POST", body: { expected_version: selected.value.version } },
    );
    await loadApplications();
  }, "申请已提交，等待初筛。");
}
async function advance() {
  await perform(async () => {
    if (!selected.value) return;
    selected.value = await $fetch<Application>(
      `/api/staff/applications/${selected.value.id}/advance`,
      {
        method: "POST",
        body: {
          expected_version: selected.value.version,
          reason: reason.value,
        },
      },
    );
    reason.value = "";
    audits.value = null;
    await loadApplications();
  }, "申请已进入初筛，原因和执行主体已记录。");
}
async function refresh() {
  await perform(async () => {
    await loadApplications();
    if (selected.value)
      selected.value = await $fetch<Application>(
        `${endpoint.value}/${selected.value.id}`,
      );
    audits.value = null;
    if (selected.value && !isStaff.value)
      Object.assign(draft, {
        name: selected.value.name,
        contact_email: selected.value.contact_email,
        statement: selected.value.statement,
      });
  }, "已获取最新状态。");
}
async function setFilter(value: string) {
  await perform(async () => {
    filter.value = value;
    offset.value = 0;
    selected.value = null;
    audits.value = null;
    await loadApplications();
  });
}
async function turnPage(delta: number) {
  await perform(async () => {
    offset.value += delta;
    selected.value = null;
    await loadApplications();
  });
}
async function readAudit() {
  await perform(async () => {
    if (selected.value)
      audits.value = await $fetch<Audit[]>(
        `/api/staff/applications/${selected.value.id}/audit`,
      );
  });
}
async function showDelegations() {
  await perform(async () => {
    section.value = "delegations";
    issuedToken.value = "";
    grantPermissions.value = [...(account.value?.permissions || [])];
    delegations.value = await $fetch<Delegation[]>("/api/delegations");
  });
}
async function issueDelegation() {
  await perform(async () => {
    const result = await $fetch<{ token: string; id: string }>(
      "/api/delegations",
      {
        method: "POST",
        body: {
          permissions: grantPermissions.value,
          application_ids:
            grantScope.value === "current" && selected.value
              ? [selected.value.id]
              : null,
          minutes: 15,
        },
      },
    );
    issuedToken.value = result.token;
    issuedId.value = result.id;
    delegations.value = await $fetch<Delegation[]>("/api/delegations");
  });
}
async function revoke(id: string) {
  await perform(async () => {
    await $fetch(`/api/delegations/${id}`, { method: "DELETE" });
    if (issuedId.value === id) issuedToken.value = "";
    delegations.value = await $fetch<Delegation[]>("/api/delegations");
  }, "委托已撤销。");
}
onMounted(async () => {
  try {
    account.value = await $fetch<Account>("/api/auth/me");
    draft.contact_email = account.value.email;
    await loadApplications();
    if (!isStaff.value && applications.value[0]) {
      selected.value = await $fetch<Application>(
        `${endpoint.value}/${applications.value[0].id}`,
      );
      Object.assign(draft, {
        name: selected.value.name,
        contact_email: selected.value.contact_email,
        statement: selected.value.statement,
      });
    }
  } catch (e) {
    if ((e as { status?: number }).status !== 401) error.value = e;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div :class="{ 'public-site': !account }">
    <header class="topbar" :inert="authOpen">
      <a class="brand voxnova-brand" href="/" :aria-label="t('Voxnova 首页')">
        <span class="voxnova-mark" aria-hidden="true">v<span>✳</span></span>
        <span
          >Voxnova<span class="brand-secondary">{{
            t("让热爱，有回响")
          }}</span></span
        >
      </a>
      <nav
        v-if="!account && !loading"
        class="public-nav"
        :aria-label="t('首页导航')"
      >
        <a href="#position">{{ t("教师岗位") }}</a
        ><a href="#process">{{ t("申请流程") }}</a
        ><a href="#faq">{{ t("常见问题") }}</a>
      </nav>
      <div class="topbar-right">
        <div
          v-if="!isStaff"
          class="language-switch"
          role="group"
          aria-label="中文 / English"
        >
          <button
            type="button"
            lang="zh-CN"
            :aria-pressed="locale === 'zh'"
            @click="setLocale('zh')"
          >
            中文
          </button>
          <span aria-hidden="true">/</span>
          <button
            type="button"
            lang="en"
            :aria-pressed="locale === 'en'"
            @click="setLocale('en')"
          >
            English
          </button>
        </div>
        <template v-if="account"
          ><span class="account-email">{{ account.email }}</span
          ><button class="text-button" :disabled="busy" @click="logout">
            {{ t("退出登录") }}
          </button></template
        ><button
          v-else-if="!loading"
          class="button small"
          @click="
            authOpen = true;
            authMode = 'login';
            error = '';
          "
        >
          {{ t("登录工作台") }}<span aria-hidden="true">↗</span>
        </button>
      </div>
    </header>
    <div v-if="loading" class="loading" role="status">
      {{ t("正在连接工作台…") }}
    </div>
    <div v-else :inert="authOpen">
      <div v-if="error" class="message error" role="alert">
        {{ displayError
        }}<button
          class="text-button"
          @click="error = ''"
          :aria-label="t('关闭错误')"
        >
          ×
        </button>
      </div>
      <div v-if="notice" class="message success" role="status">
        {{ t(notice) }}
      </div>
      <RecruitmentHome v-if="!account" @apply="openAuth('register')" />
      <div v-else class="workspace">
        <aside class="sidebar">
          <div class="workspace-label">
            {{ isStaff ? "内部工作台" : t("申请人门户")
            }}<span>{{ isStaff ? "工作台" : t("申请人门户") }}</span>
          </div>
          <nav :aria-label="t('工作台导航')">
            <button
              :class="{ active: section === 'applications' }"
              @click="
                section = 'applications';
                issuedToken = '';
              "
            >
              <span aria-hidden="true">▤</span
              >{{ isStaff ? "申请管理" : t("我的申请")
              }}<span class="nav-arrow">↗</span></button
            ><button
              v-if="isStaff"
              :class="{ active: section === 'delegations' }"
              :disabled="busy"
              @click="showDelegations"
            >
              <span aria-hidden="true">◇</span>{{ t("AI 委托") }}
            </button>
          </nav>
          <div class="sidebar-bottom">
            <span class="status-dot" /><strong>{{ t("仅演示数据") }}</strong>
            <p>{{ t("核心招聘 POC") }}<br />{{ t("当前流程止于初筛。") }}</p>
          </div>
        </aside>
        <main class="workspace-main">
          <template v-if="section === 'applications'">
            <div class="page-title">
              <div>
                <span class="eyebrow">{{
                  isStaff ? "招聘" : t("YOUR NEXT CHAPTER")
                }}</span>
                <h1>
                  {{ isStaff ? "申请管理" : t("我的申请")
                  }}<span class="title-dot">.</span>
                </h1>
                <p>
                  {{
                    isStaff
                      ? "每一份申请，都值得认真对待。"
                      : t("完善你的资料，并在这里查看每一步。")
                  }}
                </p>
              </div>
              <button
                class="button secondary small"
                :disabled="busy"
                @click="refresh"
              >
                <span aria-hidden="true">↻</span>{{ t("刷新") }}
              </button>
            </div>
            <template v-if="isStaff">
              <div class="stat-row">
                <div>
                  <span>当前页申请</span
                  ><strong>{{
                    applications.length.toString().padStart(2, "0")
                  }}</strong>
                </div>
                <div>
                  <span>等待初筛</span
                  ><strong
                    >{{ counts.submitted.toString().padStart(2, "0")
                    }}<i class="status-dot amber"
                  /></strong>
                </div>
                <div>
                  <span>已进入初筛</span
                  ><strong
                    >{{ counts.screening.toString().padStart(2, "0")
                    }}<i class="status-dot"
                  /></strong>
                </div>
                <div class="stat-note">草稿仅本人可见<br />每页最多 50 份</div>
              </div>
              <div class="content-grid" :class="{ 'has-detail': selected }">
                <section class="panel list-panel">
                  <div class="panel-toolbar">
                    <div class="tabs" aria-label="按状态筛选">
                      <button
                        :class="{ active: !filter }"
                        :disabled="busy"
                        @click="setFilter('')"
                      >
                        全部</button
                      ><button
                        :class="{ active: filter === 'submitted' }"
                        :disabled="busy"
                        @click="setFilter('submitted')"
                      >
                        {{ t("已提交") }}</button
                      ><button
                        :class="{ active: filter === 'screening' }"
                        :disabled="busy"
                        @click="setFilter('screening')"
                      >
                        {{ t("初筛") }}
                      </button>
                    </div>
                    <span class="muted"
                      >{{ applications.length ? offset + 1 : 0 }}–{{
                        offset + applications.length
                      }}</span
                    >
                  </div>
                  <div v-if="!can('applications.read')" class="empty">
                    <span>◇</span>
                    <h3>暂无查看权限</h3>
                    <p>请由初始化人员确认本账号权限。</p>
                  </div>
                  <div v-else-if="!applications.length" class="empty">
                    <span>▤</span>
                    <h3>
                      {{ filter ? "当前筛选暂无申请" : "这里还没有申请" }}
                    </h3>
                    <p>
                      {{
                        filter
                          ? "切换状态筛选，查看其他申请。"
                          : "申请人提交后，资料会出现在这里。"
                      }}
                    </p>
                  </div>
                  <div v-else class="application-list">
                    <button
                      v-for="item in applications"
                      :key="item.id"
                      class="application-row"
                      :class="{ selected: selected?.id === item.id }"
                      :disabled="busy"
                      :aria-label="`查看 ${item.name} 的申请`"
                      @click="openApplication(item)"
                    >
                      <span class="avatar">{{
                        item.name.slice(0, 1).toUpperCase()
                      }}</span>
                      <div class="applicant-info">
                        <strong>{{ item.name }}</strong
                        ><small>{{ item.contact_email }}</small
                        ><small>{{ formatTime(item.created_at) }}</small>
                      </div>
                      <span class="pill" :class="item.status">{{
                        statusLabel[item.status]
                      }}</span
                      ><span class="row-arrow">↗</span>
                    </button>
                  </div>
                  <div class="pagination">
                    <button
                      class="text-button"
                      :disabled="busy || offset === 0"
                      @click="turnPage(-50)"
                    >
                      ← 上一页</button
                    ><button
                      class="text-button"
                      :disabled="busy || applications.length < 50"
                      @click="turnPage(50)"
                    >
                      下一页 →
                    </button>
                  </div>
                </section>
                <section
                  v-if="selected"
                  class="panel detail-panel"
                  aria-label="申请详情"
                >
                  <div class="detail-header">
                    <span class="eyebrow">申请详情</span
                    ><button
                      class="text-button"
                      aria-label="关闭详情"
                      @click="
                        selected = null;
                        audits = null;
                      "
                    >
                      ×
                    </button>
                  </div>
                  <div class="detail-person">
                    <span class="avatar large">{{
                      selected.name.slice(0, 1)
                    }}</span>
                    <div>
                      <h2>{{ selected.name }}</h2>
                      <p>{{ selected.contact_email }}</p>
                    </div>
                  </div>
                  <span
                    class="pill"
                    :class="selected.status"
                    data-testid="detail-status"
                    >{{ statusLabel[selected.status] }}</span
                  >
                  <div class="detail-field">
                    <h3>{{ t("申请说明") }}</h3>
                    <p class="preserve">{{ selected.statement }}</p>
                  </div>
                  <div class="detail-field">
                    <h3>申请信息</h3>
                    <dl>
                      <dt>演示职位</dt>
                      <dd>{{ t("在线英语教师") }}</dd>
                      <dt>最后更新</dt>
                      <dd>{{ formatTime(selected.updated_at) }}</dd>
                      <dt>申请编号</dt>
                      <dd class="mono">{{ selected.id }}</dd>
                    </dl>
                  </div>
                  <form
                    v-if="
                      selected.status === 'submitted' &&
                      can('applications.advance')
                    "
                    class="advance-form"
                    @submit.prevent="advance"
                  >
                    <label for="reason"
                      >初筛推进原因 <span class="required">*</span></label
                    ><textarea
                      id="reason"
                      v-model="reason"
                      required
                      minlength="1"
                      maxlength="1000"
                      rows="3"
                      placeholder="填写推进至初筛的原因…"
                    /><button
                      class="button full"
                      :disabled="busy || !reason.trim()"
                    >
                      推进至初筛 <span aria-hidden="true">→</span></button
                    ><small>操作将保存状态事件与审计记录。</small>
                  </form>
                  <div v-if="selected.status === 'screening'" class="info-note">
                    已进入初筛。本 POC 暂不包含后续流程。
                  </div>
                  <div class="detail-field">
                    <h3>
                      {{ t("状态记录")
                      }}<span class="muted">{{ selected.events.length }}</span>
                    </h3>
                    <ol class="timeline">
                      <li v-for="event in selected.events" :key="event.id">
                        <strong
                          >{{ statusLabel[event.after]
                          }}<span class="channel">{{
                            event.channel === "ai" ? t("AI 委托") : t("网页")
                          }}</span></strong
                        >
                        <p>{{ eventReason(event) }}</p>
                        <small>{{ formatTime(event.at) }}</small
                        ><small class="mono"
                          >执行主体：{{ event.actor_id }}</small
                        ><small v-if="event.delegated_by" class="mono"
                          >委托人：{{ event.delegated_by }}</small
                        >
                      </li>
                    </ol>
                  </div>
                  <button
                    v-if="can('audit.read')"
                    class="button secondary full"
                    :disabled="busy"
                    @click="readAudit"
                  >
                    查看此申请审计记录 ↗
                  </button>
                  <div
                    v-if="audits"
                    class="audit-list"
                    tabindex="0"
                    aria-label="审计记录"
                  >
                    <p class="muted">最近 {{ audits.length }} 条记录</p>
                    <article v-for="row in audits" :key="row.id">
                      <strong
                        >{{ row.action }}
                        <span class="channel">{{ row.channel }}</span></strong
                      ><small>{{ formatTime(row.at) }} · {{ row.result }}</small
                      ><small class="mono">{{ row.actor_id }}</small
                      ><small v-if="row.delegated_by"
                        >委托人：{{ row.delegated_by }}</small
                      >
                      <pre>{{ JSON.stringify(row.data, null, 2) }}</pre>
                    </article>
                  </div>
                </section>
                <div v-else-if="applications.length" class="detail-placeholder">
                  <span>↗</span>
                  <p>选择一份申请，查看资料与状态记录。</p>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="progress-steps" :aria-label="t('申请流程')">
                <div
                  v-for="(status, i) in [
                    'draft',
                    'submitted',
                    'screening',
                  ] as Status[]"
                  :key="status"
                  :class="{
                    reached:
                      i <=
                      (selected
                        ? ['draft', 'submitted', 'screening'].indexOf(
                            selected.status,
                          )
                        : 0),
                  }"
                >
                  <span>{{ String(i + 1).padStart(2, "0") }}</span
                  ><strong>{{ statusLabel[status] }}</strong>
                </div>
              </div>
              <div class="applicant-grid">
                <section class="panel applicant-form">
                  <div class="section-heading">
                    <h2>{{ t("申请资料") }}</h2>
                    <span
                      class="pill"
                      :class="selected?.status || 'draft'"
                      data-testid="own-status"
                      >{{ statusLabel[selected?.status || "draft"] }}</span
                    >
                  </div>
                  <p class="muted form-intro">
                    {{ t("演示职位 · 在线英语教师。请使用样例姓名和邮箱。") }}
                  </p>
                  <form
                    v-if="!selected || selected.status === 'draft'"
                    novalidate
                    @submit.prevent="saveDraft"
                  >
                    <label for="applicant-name"
                      >{{ t("姓名") }}<span class="required">*</span></label
                    ><input
                      id="applicant-name"
                      v-model="draft.name"
                      required
                      maxlength="100"
                      autocomplete="off"
                      :placeholder="t('例如：Alex Chen（演示）')"
                    /><label for="contact-email"
                      >{{ t("联系邮箱") }}<span class="required">*</span></label
                    ><input
                      id="contact-email"
                      v-model="draft.contact_email"
                      required
                      type="email"
                      maxlength="254"
                      placeholder="alex@example.com"
                    /><label for="statement"
                      >{{ t("申请说明") }}<span class="required">*</span></label
                    ><textarea
                      id="statement"
                      v-model="draft.statement"
                      required
                      maxlength="5000"
                      rows="7"
                      :placeholder="
                        t('简单介绍教学经验或申请意向，仅填写演示内容。')
                      "
                    />
                    <div class="form-hint">
                      {{ draft.statement.length }} / 5000
                      <span>{{ t("提交后资料将锁定，请先保存并核对。") }}</span>
                    </div>
                    <div class="form-actions">
                      <button class="button secondary" :disabled="busy">
                        {{ selected ? t("保存修改") : t("保存草稿") }}</button
                      ><button
                        v-if="selected"
                        type="button"
                        class="button"
                        :disabled="
                          busy ||
                          draft.name !== selected.name ||
                          draft.contact_email !== selected.contact_email ||
                          draft.statement !== selected.statement
                        "
                        @click="submitApplication"
                      >
                        {{ t("确认提交 →") }}
                      </button>
                    </div>
                  </form>
                  <template v-else
                    ><div class="info-note">
                      {{
                        selected.status === "submitted"
                          ? t("申请已提交，等待初筛。提交后的资料不可编辑。")
                          : t("申请已进入初筛。当前 POC 流程在此结束。")
                      }}
                    </div>
                    <dl class="submitted-fields">
                      <dt>{{ t("姓名") }}</dt>
                      <dd>{{ selected.name }}</dd>
                      <dt>{{ t("联系邮箱") }}</dt>
                      <dd>{{ selected.contact_email }}</dd>
                      <dt>{{ t("申请说明") }}</dt>
                      <dd class="preserve">{{ selected.statement }}</dd>
                    </dl></template
                  >
                </section>
                <aside class="applicant-help">
                  <span class="eyebrow">{{ t("EVERY STEP, RECORDED") }}</span>
                  <h2>
                    {{ t("申请的每一步，") }}<br />{{ t("都清晰可见。") }}
                  </h2>
                  <p>
                    {{
                      t(
                        "草稿仅你本人可见。提交后，内部员工可查看并推进至初筛。",
                      )
                    }}
                  </p>
                  <div v-if="selected" class="detail-field">
                    <h3>{{ t("状态记录") }}</h3>
                    <ol class="timeline">
                      <li v-for="event in selected.events" :key="event.id">
                        <strong
                          >{{ statusLabel[event.after] }}
                          <span class="channel">{{
                            event.channel === "ai" ? t("AI 委托") : t("网页")
                          }}</span></strong
                        >
                        <p>{{ eventReason(event) }}</p>
                        <small>{{ formatTime(event.at) }}</small>
                      </li>
                    </ol>
                  </div>
                  <p v-else class="help-note">
                    {{ t("先保存草稿，再确认提交。") }}<br />{{
                      t("本次演示仅支持一份申请。")
                    }}
                  </p>
                </aside>
              </div>
            </template>
          </template>
          <template v-else>
            <div class="page-title">
              <div>
                <span class="eyebrow">委托访问</span>
                <h1>{{ t("AI 委托") }}<span class="title-dot">.</span></h1>
                <p>通过短期授权，让 AI 在你的权限范围内协助工作。</p>
              </div>
            </div>
            <div class="delegation-grid">
              <section class="panel">
                <h2>创建受限委托</h2>
                <p class="muted">
                  有效期 15 分钟，可随时撤销。令牌只显示一次。
                </p>
                <form @submit.prevent="issueDelegation">
                  <fieldset>
                    <legend>授权能力</legend>
                    <label
                      v-for="permission in account.permissions"
                      :key="permission"
                      class="checkbox"
                      ><input
                        v-model="grantPermissions"
                        type="checkbox"
                        :value="permission"
                      />{{
                        {
                          "applications.read": "查询申请列表与详情",
                          "applications.advance": "推进至初筛",
                          "audit.read": "读取申请审计",
                        }[permission] || permission
                      }}</label
                    >
                  </fieldset>
                  <label for="scope">申请范围</label
                  ><select id="scope" v-model="grantScope">
                    <option value="current" :disabled="!selected">
                      {{
                        selected
                          ? `仅当前申请：${selected.name}`
                          : "请先在申请管理中选择申请"
                      }}
                    </option>
                    <option value="all">本人可访问的全部申请</option>
                  </select>
                  <p class="muted">委托会随本人权限收窄而失效或缩小范围。</p>
                  <button
                    class="button"
                    :disabled="
                      busy ||
                      !grantPermissions.length ||
                      (grantScope === 'current' && !selected)
                    "
                  >
                    生成委托令牌 ↗
                  </button>
                </form>
                <div v-if="issuedToken" class="token-box">
                  <label for="issued-token">AI 委托令牌 · 请妥善保存</label
                  ><input
                    id="issued-token"
                    :value="issuedToken"
                    readonly
                    autocomplete="off"
                    spellcheck="false"
                  />
                  <p>切换页面后不再显示。不要写入代码、审计或报告。</p>
                </div>
              </section>
              <section class="panel">
                <h2>最近委托</h2>
                <p class="muted">最多显示最近 50 项。OpenAPI：后端 /docs。</p>
                <p v-if="!delegations.length" class="empty">暂无委托。</p>
                <article
                  v-for="grant in delegations"
                  :key="grant.id"
                  class="grant"
                >
                  <div>
                    <span
                      class="pill"
                      :class="
                        grant.revoked || grant.expired ? 'neutral' : 'screening'
                      "
                      >{{
                        grant.revoked
                          ? "已撤销"
                          : grant.expired
                            ? "已过期"
                            : "有效"
                      }}</span
                    ><button
                      v-if="!grant.revoked && !grant.expired"
                      class="text-button"
                      :disabled="busy"
                      @click="revoke(grant.id)"
                    >
                      撤销
                    </button>
                  </div>
                  <p class="mono">{{ grant.id }}</p>
                  <small>{{ grant.permissions.join(" · ") }}</small
                  ><small>{{
                    grant.application_ids
                      ? `范围：${grant.application_ids.join(", ")}`
                      : "范围：本人可访问的全部申请"
                  }}</small
                  ><small>到期：{{ formatTime(grant.expires_at) }}</small>
                </article>
              </section>
            </div>
          </template>
          <footer class="workspace-footer">
            <span>{{ t("Voxnova · 招聘工作台") }}</span
            ><span>{{ t("演示资料 / 三状态流程 / 可追溯操作") }}</span>
          </footer>
        </main>
      </div>
    </div>
    <div
      v-if="authOpen && !account"
      class="modal-backdrop"
      @click.self="authOpen = false"
    >
      <section
        class="auth-modal"
        ref="authDialog"
        @keydown.tab="trapAuthFocus"
        @keydown.esc.prevent="authOpen = false"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-heading"
      >
        <button
          class="modal-close text-button"
          :aria-label="t('关闭登录')"
          @click="authOpen = false"
        >
          ×
        </button>
        <div
          class="language-switch auth-language-switch"
          role="group"
          aria-label="中文 / English"
        >
          <button
            type="button"
            lang="zh-CN"
            :aria-pressed="locale === 'zh'"
            @click="setLocale('zh')"
          >
            中文
          </button>
          <span aria-hidden="true">/</span>
          <button
            type="button"
            lang="en"
            :aria-pressed="locale === 'en'"
            @click="setLocale('en')"
          >
            English
          </button>
        </div>
        <span class="eyebrow">{{ t("WELCOME TO VOXNOVA") }}</span>
        <h2 id="auth-heading">
          {{ authMode === "register" ? t("开始你的申请") : t("欢迎回来")
          }}<span class="title-dot">.</span>
        </h2>
        <p class="muted">
          {{
            authMode === "register"
              ? t("创建申请人账号，开始填写申请资料。")
              : t("申请人和内部员工使用各自账号登录。")
          }}
        </p>
        <div class="tabs auth-tabs">
          <button
            :class="{ active: authMode === 'login' }"
            @click="
              authMode = 'login';
              error = '';
            "
          >
            {{ t("登录") }}</button
          ><button
            :class="{ active: authMode === 'register' }"
            @click="
              authMode = 'register';
              error = '';
            "
          >
            {{ t("注册申请人") }}
          </button>
        </div>
        <form novalidate @submit.prevent="authenticate">
          <label for="auth-email">{{ t("邮箱") }}</label
          ><input
            id="auth-email"
            v-model="email"
            autofocus
            required
            type="email"
            maxlength="254"
            autocomplete="username"
            placeholder="name@example.com"
          /><label for="auth-password">{{ t("密码") }}</label
          ><input
            id="auth-password"
            v-model="password"
            required
            type="password"
            minlength="12"
            maxlength="128"
            :autocomplete="
              authMode === 'register' ? 'new-password' : 'current-password'
            "
            :placeholder="t('12–128 个字符')"
          /><small class="muted">{{
            authMode === "register"
              ? t("内部员工由专用初始化命令创建。")
              : t("请使用你自己的账号登录。")
          }}</small
          ><button class="button full" :disabled="busy">
            {{
              busy
                ? t("处理中…")
                : authMode === "register"
                  ? t("创建账号并继续 →")
                  : t("登录 →")
            }}
          </button>
        </form>
        <div v-if="error" class="auth-error" role="alert">
          {{ displayError }}
        </div>
      </section>
    </div>
  </div>
</template>
