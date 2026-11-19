<script setup lang="ts">
defineEmits<{ apply: [event: MouseEvent] }>();
const { locale, t } = useLocale();
</script>

<template>
  <main id="main-content" tabindex="-1" class="recruitment-home">
    <section id="position" class="wrap hero" aria-labelledby="role-title">
      <div class="hero-copy">
        <p class="eyeline">{{ t("Voxnova 教师招聘") }}</p>
        <h1 id="role-title">
          <span>{{ t("在线英语") }}{{ locale === "en" ? " " : "" }}</span
          ><span>{{ t("教师") }}</span>
        </h1>
        <p class="intro">
          {{
            t(
              "想来教英语？写下你的教学经历，或说说你为什么想成为教师。申请可以先存为草稿，准备好再提交。",
            )
          }}
        </p>
        <div class="actions">
          <button class="primary" type="button" @click="$emit('apply', $event)">
            {{ t("开始申请") }} <span aria-hidden="true">→</span></button
          ><a href="#process"
            >{{ t("了解申请流程") }} <span aria-hidden="true">↓</span></a
          >
        </div>
      </div>
      <figure class="sheet" :aria-label="t('英语口语课示例')">
        <div class="paper" lang="en">
          <div class="sheet-label">
            <b>VOXNOVA</b><span>ENGLISH NOTES</span>
          </div>
          <p class="lesson-label">CONVERSATION PRACTICE</p>
          <p class="phrase">Tell me <em>more</em> about it.</p>
          <p class="annotation">
            <span aria-hidden="true">↳ </span>Invite a longer answer.
          </p>
          <p class="answer">“What happened next?”</p>
        </div>
      </figure>
    </section>
    <section class="band" id="process">
      <div class="wrap section">
        <h2>{{ t("申请怎么走") }}</h2>
        <ol>
          <li>
            <strong>{{ t("填写申请资料") }}</strong>
            <p>
              {{
                t(
                  "创建账号，填写姓名、联系邮箱和申请说明。写到一半可以保存草稿。",
                )
              }}
            </p>
          </li>
          <li>
            <strong>{{ t("核对后提交") }}</strong>
            <p>{{ t("提交后资料会锁定，请先核对邮箱和申请说明。") }}</p>
          </li>
          <li>
            <strong>{{ t("查看初筛状态") }}</strong>
            <p>
              {{
                t("登录申请人门户，查看最新状态和记录。当前流程到初筛为止。")
              }}
            </p>
          </li>
        </ol>
      </div>
    </section>
    <section id="faq" class="wrap section">
      <h2>{{ t("申请前常见问题") }}</h2>
      <div>
        <details open>
          <summary>{{ t("资料没写完，可以下次继续吗？") }}</summary>
          <p>
            {{
              t(
                "可以。先保存草稿，下次登录同一账号继续填写。草稿仅你本人可见。",
              )
            }}
          </p>
        </details>
        <details>
          <summary>{{ t("提交后还能修改吗？") }}</summary>
          <p>{{ t("提交后资料将锁定，请在提交前仔细核对。") }}</p>
        </details>
        <details>
          <summary>{{ t("在哪里查看申请状态？") }}</summary>
          <p>{{ t("登录申请人门户即可查看最新状态及状态记录。") }}</p>
        </details>
      </div>
    </section>
    <footer class="wrap footer">
      <span lang="en" class="public-wordmark">Voxnova<i>.</i></span
      ><a href="#main-content">{{ t("回到顶部 ↑") }}</a>
    </footer>
  </main>
</template>

<style scoped>
.recruitment-home {
  font-size: 16px;
  line-height: 1.65;
  overflow-wrap: break-word;
}
.wrap {
  width: var(--home-width);
  margin-inline: auto;
}
.primary {
  border: 1px solid var(--home-ink);
  border-radius: 5px;
  background: var(--home-ink);
  color: white;
  min-height: 46px;
  padding: 12px 23px;
  font-weight: 650;
}
.primary:hover {
  background: #315747;
}
.primary:active {
  transform: translateY(1px);
}
.actions a,
.footer a {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
  min-height: 44px;
  text-decoration: underline;
  text-underline-offset: 5px;
}
.hero > *,
.section > * {
  min-width: 0;
}
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6%;
  align-items: center;
  min-height: clamp(590px, calc(100svh - 78px), 850px);
  padding: 54px 0;
}
.eyeline {
  font-size: 15px;
  font-weight: 650;
  color: #8e422c;
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 20px;
}
.eyeline:before {
  content: "";
  height: 2px;
  width: 35px;
  background: currentColor;
}
h1,
h2 {
  font-family: Georgia, "Noto Serif CJK SC", "Songti SC", "SimSun", serif;
  font-weight: 500;
}
h1 {
  font-size: clamp(54px, 6vw, 96px);
  letter-spacing: -0.065em;
  line-height: 1.13;
  margin: 0;
}
h1 span {
  display: block;
}
h1 span:last-child {
  color: #44614c;
}
.intro {
  max-width: 31em;
  margin: 26px 0 28px;
  color: #46594f;
}
.actions {
  display: flex;
  gap: 23px;
  align-items: center;
  flex-wrap: wrap;
}
.sheet {
  background: #eadabb;
  color: #253c34;
  margin: 0;
  padding: clamp(24px, 4vw, 66px);
  position: relative;
  min-width: 0;
  min-height: 420px;
  display: flex;
  align-items: center;
}
.paper {
  background: #fff9e7;
  width: 100%;
  padding: 23px clamp(18px, 2.6vw, 45px) 32px;
  box-shadow: 5px 6px 0 #af9e7952;
  position: relative;
  border-top: 5px solid #9d482f;
}
.sheet-label,
.lesson-label {
  font:
    600 11px/1.5 ui-monospace,
    monospace;
  letter-spacing: 0.11em;
}
.sheet-label {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  justify-content: space-between;
  border-bottom: 1px solid #c7bda5;
  padding-bottom: 13px;
  color: #645f4e;
}
.lesson-label {
  margin: 26px 0 10px;
  color: #8b442e;
}
.phrase {
  max-inline-size: 6.6em;
  font:
    normal clamp(33px, 3.65vw, 64px) / 1.07 Georgia,
    serif;
  letter-spacing: -0.05em;
  margin: 0;
}
.phrase em {
  color: #91432d;
  border-bottom: 2px solid;
}
.annotation {
  color: #87452f;
  font:
    italic 17px/1.45 Georgia,
    serif;
  margin: 12px 0 23px;
}
.answer {
  border-top: 1px solid #c7bda5;
  padding-top: 15px;
  margin: 0;
  font:
    italic clamp(20px, 2vw, 31px) / 1.2 Georgia,
    serif;
}
.band {
  background: #e7ebdf;
}
.section {
  padding: clamp(50px, 7vw, 100px) 0;
  display: grid;
  grid-template-columns: 1fr 1.45fr;
  gap: 8%;
}
h2 {
  font-size: clamp(32px, 3.8vw, 56px);
  letter-spacing: -0.055em;
  line-height: 1.2;
  margin: 0;
}
ol {
  margin: 0;
  padding: 0;
  list-style-type: decimal-leading-zero;
  padding-inline-start: 2.6em;
}
li {
  padding: 0 0 19px 10px;
  margin: 0 0 19px;
  border-bottom: 1px solid #bac4b7;
}
li:last-child {
  margin-bottom: 0;
}
li::marker {
  color: #905335;
  font: italic 24px Georgia;
}
strong {
  font-size: 19px;
}
li p,
details p {
  margin: 6px 0 0;
  color: #495c51;
}
details {
  border-bottom: 1px solid #c7c9bc;
  padding: 6px 0;
}
summary {
  min-height: 44px;
  align-content: center;
  cursor: pointer;
  font-weight: 600;
}
.footer {
  border-top: 1px solid #c7c9bc;
  padding: 26px 0;
  display: flex;
  justify-content: space-between;
}
details p {
  padding-bottom: 12px;
}
@media (prefers-reduced-motion: no-preference) {
  .hero-copy,
  .paper {
    animation: arrive 0.45s ease-out;
  }
  @keyframes arrive {
    from {
      transform: translateY(6px);
      opacity: 0.5;
    }
    to {
      transform: none;
      opacity: 1;
    }
  }
}
@media (max-width: 760px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
    gap: 32px;
    min-height: 0;
    padding: 43px 0 34px;
  }
  .intro {
    margin: 18px 0 22px;
  }
  .eyeline {
    margin-bottom: 15px;
  }
  .sheet {
    min-height: 0;
    padding: clamp(18px, 6vw, 26px);
  }
  .paper {
    max-width: 470px;
    margin: auto;
  }
  .section {
    grid-template-columns: minmax(0, 1fr);
    gap: 30px;
  }
  .footer {
    align-items: center;
  }
  .actions {
    gap: 18px;
  }
}
</style>
