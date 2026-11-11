<script setup lang="ts">
defineEmits<{ apply: []; login: [] }>();
const questions = [
  {
    title: "如何开始我的申请？",
    answer:
      "点击「开始申请」创建申请人账号，然后填写姓名、联系邮箱和申请说明。已有账号可直接登录。",
  },
  {
    title: "资料没写完，可以下次继续吗？",
    answer:
      "可以。先保存草稿，下次登录后可以继续编辑。草稿仅你本人可见，请在确认无误后提交。",
  },
  {
    title: "提交后还能修改吗？",
    answer:
      "提交后的资料将锁定，不能继续编辑。请在提交前仔细核对姓名、联系邮箱和申请说明。",
  },
  {
    title: "在哪里查看申请状态？",
    answer:
      "登录申请人门户即可查看最新状态和状态记录。当前线上申请流程支持草稿、已提交和初筛；初筛不代表录用。",
  },
];
</script>

<template>
  <main id="main-content" class="recruitment-home">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">
          HELLO, FUTURE EDUCATOR <span aria-hidden="true">↗</span>
        </p>
        <h1 id="hero-title">
          让热爱教学的你，<br />被<span class="accent">更多可能</span>听见。
        </h1>
        <p class="hero-intro">
          每一次表达，都能打开一个新世界。<br />在
          Voxnova，开启你的在线英语教学新篇章。
        </p>
        <div class="hero-actions">
          <button class="apply-button" @click="$emit('apply')">
            开始申请 <span aria-hidden="true">↗</span>
          </button>
          <a class="discover-link" href="#position"
            >认识教师岗位 <span aria-hidden="true">↓</span></a
          >
        </div>
        <p class="hero-note">
          <span aria-hidden="true">✳</span> 从一份申请开始，让下一步清晰可见。
        </p>
      </div>
      <div
        class="hero-art"
        role="img"
        aria-label="原创教学插画：对话、书本与连接彼此的声音"
      >
        <div class="art-grid" />
        <span class="art-spark" aria-hidden="true">✳</span>
        <div class="lesson-card" aria-hidden="true">
          <div class="lesson-top">
            <span class="lesson-dot" /> VOXNOVA CLASSROOM <span>↗</span>
          </div>
          <div class="lesson-board">
            <span class="board-caption">A little curiosity.</span
            ><strong>A world<br />of <i>possibility.</i></strong
            ><span class="board-line" />
          </div>
          <div class="lesson-bottom">
            <span class="voice-bars"><i /><i /><i /><i /><i /></span
            ><span>YOUR VOICE. THEIR NEW WORLD.</span>
          </div>
        </div>
        <div class="hello-bubble" aria-hidden="true">
          Hello<span>你好，新的可能！</span>
        </div>
        <svg class="book" viewBox="0 0 240 180" aria-hidden="true">
          <path
            d="M22 33 Q68 11 120 40 Q172 11 218 33 L218 144 Q167 125 120 154 Q73 125 22 144Z"
            fill="#ffe5ad"
            stroke="#343a34"
            stroke-width="3"
          />
          <path
            d="M120 40V154M42 53Q75 40 101 55M42 72Q75 59 101 74M42 91Q75 78 101 93M141 56Q171 40 197 53M141 75Q171 59 197 72"
            fill="none"
            stroke="#9b723e"
            stroke-width="3"
            stroke-linecap="round"
          />
          <path
            d="M29 152Q76 137 120 163Q168 137 212 152"
            fill="none"
            stroke="#343a34"
            stroke-width="3"
          />
        </svg>
        <span class="art-label" aria-hidden="true"
          >CONNECT THROUGH ENGLISH</span
        >
      </div>
    </section>

    <div class="chapter-strip" aria-hidden="true">
      <span>YOUR VOICE MATTERS</span><span>✳</span><span>用英语连接世界</span
      ><span>✳</span><span>A NEW CHAPTER STARTS HERE</span>
    </div>

    <section
      id="position"
      class="position-section"
      aria-labelledby="position-title"
    >
      <div class="section-intro">
        <p class="eyebrow">01 / THE OPPORTUNITY</p>
        <h2 id="position-title">把你的热爱，<br />带进下一间课堂。</h2>
        <p>从介绍自己开始，<br />让我们认识你与英语教学的故事。</p>
      </div>
      <article class="opportunity-card">
        <div class="opportunity-top">
          <span class="role-icon" aria-hidden="true">Aa</span
          ><span class="role-label">教师岗位</span>
        </div>
        <h3>在线英语教师</h3>
        <p class="english-label">Online English Teacher</p>
        <p class="role-description">
          在申请说明中分享你的教学经验或申请意向。先保存、再核对，准备好后提交，让每一步都有记录。
        </p>
        <div class="role-facts">
          <span>线上申请</span><span>支持草稿保存</span><span>状态可查询</span>
        </div>
        <button class="inline-action" @click="$emit('apply')">
          从这里开启申请 <span aria-hidden="true">↗</span>
        </button>
      </article>
    </section>

    <section
      id="process"
      class="process-section"
      aria-labelledby="process-title"
    >
      <div class="section-heading-row">
        <div>
          <p class="eyebrow">02 / YOUR NEXT STEPS</p>
          <h2 id="process-title">三步，走向新的开始。</h2>
        </div>
        <p>按自己的节奏准备，<br />在同一个地方查看申请状态。</p>
      </div>
      <ol class="process-grid">
        <li>
          <span class="step-number">01 <span aria-hidden="true">↗</span></span>
          <h3>介绍自己</h3>
          <p>创建账号，填写姓名、联系邮箱和申请说明，随时保存草稿。</p>
          <span class="step-caption">TELL YOUR STORY</span>
        </li>
        <li>
          <span class="step-number">02 <span aria-hidden="true">↗</span></span>
          <h3>确认并提交</h3>
          <p>核对资料后正式提交。提交后资料将锁定，请先确认填写无误。</p>
          <span class="step-caption">TAKE THE FIRST STEP</span>
        </li>
        <li>
          <span class="step-number">03 <span aria-hidden="true">✳</span></span>
          <h3>查看初筛状态</h3>
          <p>内部员工查看申请并推进初筛。登录门户，查看最新状态与记录。</p>
          <span class="step-caption">STAY IN THE LOOP</span>
        </li>
      </ol>
    </section>

    <section id="faq" class="faq-section" aria-labelledby="faq-title">
      <div class="section-intro">
        <p class="eyebrow">03 / GOOD TO KNOW</p>
        <h2 id="faq-title">你可能想知道。</h2>
        <p>开始之前，<br />让申请少一点疑问。</p>
      </div>
      <div class="faq-list">
        <details v-for="question in questions" :key="question.title">
          <summary>
            {{ question.title
            }}<span class="faq-plus" aria-hidden="true">+</span>
          </summary>
          <p>{{ question.answer }}</p>
        </details>
      </div>
    </section>

    <section class="closing" aria-labelledby="closing-title">
      <span class="closing-spark" aria-hidden="true">✳</span>
      <p class="eyebrow">THE NEXT CHAPTER IS YOURS</p>
      <h2 id="closing-title">你的声音，值得被听见。</h2>
      <p>让一份认真准备的申请，成为新的起点。</p>
      <button class="apply-button" @click="$emit('apply')">
        创建申请人账号 <span aria-hidden="true">↗</span></button
      ><button class="closing-login" @click="$emit('login')">
        已有账号？登录 →
      </button>
    </section>
    <footer class="home-footer">
      <span class="footer-wordmark">Voxnova<span>让热爱，有回响</span></span>
      <p>
        在线英语教师招聘<br /><span
          >当前申请流程：填写资料 · 提交申请 · 初筛</span
        >
      </p>
      <a href="#main-content">回到顶部 ↑</a>
    </footer>
  </main>
</template>

<style scoped>
.recruitment-home {
  --ink: #252c2b;
  --orange: #bd4325;
  --line: #e5ded3;
  --muted: #656b66;
  color: var(--ink);
}
.recruitment-home .eyebrow {
  color: #8e4934;
  font-size: 11px;
  letter-spacing: 1.6px;
  font-weight: 650;
}
.hero {
  max-width: 1248px;
  margin: auto;
  padding: 78px 24px 72px;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  align-items: center;
  gap: 42px;
}
.hero-copy .eyebrow {
  display: flex;
  align-items: center;
  gap: 22px;
}
h1 {
  font-size: clamp(38px, 3.8vw, 56px);
  line-height: 1.5;
  font-weight: 750;
  letter-spacing: -2px;
  margin: 24px 0 22px;
}
.accent {
  color: var(--orange);
  position: relative;
  white-space: nowrap;
}
.accent::after {
  content: "";
  position: absolute;
  height: 7px;
  border-radius: 50%;
  border-top: 2px solid var(--orange);
  bottom: -8px;
  left: 0;
  right: 0;
  transform: rotate(-3deg);
}
.hero-intro {
  color: var(--muted);
  font-size: 15px;
  line-height: 2;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 28px;
  margin-top: 32px;
  flex-wrap: wrap;
}
.apply-button {
  border: 1px solid var(--orange);
  background: var(--orange);
  color: white;
  border-radius: 7px;
  padding: 15px 24px;
  min-height: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 36px;
  font-weight: 600;
}
.apply-button:hover {
  background: #9b341c;
}
.discover-link {
  font-size: 13px;
  padding: 12px 0;
  border-bottom: 1px solid #bfb5a7;
  display: inline-flex;
  gap: 16px;
}
.hero-note {
  font-size: 11px;
  color: var(--muted);
  margin-top: 32px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.hero-note > span {
  font-size: 20px;
  color: var(--orange);
}
.hero-art {
  height: 440px;
  position: relative;
  isolation: isolate;
}
.art-grid {
  position: absolute;
  inset: 10px 4px 16px 25px;
  border-radius: 48% 48% 15% 15%;
  background-color: #f3eade;
  background-image:
    linear-gradient(#e6dacb 1px, transparent 1px),
    linear-gradient(90deg, #e6dacb 1px, transparent 1px);
  background-size: 36px 36px;
  transform: rotate(4deg);
  z-index: -1;
}
.lesson-card {
  position: absolute;
  top: 65px;
  left: 20px;
  right: 28px;
  border: 1px solid #c7bdad;
  border-radius: 14px;
  background: #fffdf9;
  box-shadow: 8px 10px 0 #c7b79f33;
  transform: rotate(-5deg);
  overflow: hidden;
}
.lesson-top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 15px 18px;
  font-size: 9px;
  letter-spacing: 1.2px;
}
.lesson-top > span:last-child {
  margin-left: auto;
  font-size: 16px;
}
.lesson-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--orange);
}
.lesson-board {
  background: #304a40;
  margin: 0 12px;
  border-radius: 6px;
  padding: 23px 25px 26px;
  color: #fff6de;
  position: relative;
}
.board-caption {
  font-family: Georgia, serif;
  font-style: italic;
  font-size: 17px;
}
.lesson-board strong {
  display: block;
  font-size: clamp(28px, 3vw, 42px);
  line-height: 1.15;
  font-family: Georgia, serif;
  font-weight: 400;
  margin-top: 10px;
  letter-spacing: -1px;
}
.lesson-board i {
  color: #ffcd83;
}
.board-line {
  position: absolute;
  width: 60px;
  height: 60px;
  border: 2px dashed #98afa0;
  border-radius: 50%;
  right: 26px;
  top: 40px;
}
.lesson-bottom {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px 18px;
  font-size: 7px;
  letter-spacing: 0.8px;
}
.voice-bars {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 20px;
}
.voice-bars i {
  display: block;
  width: 3px;
  height: 9px;
  background: var(--orange);
  border-radius: 3px;
}
.voice-bars i:nth-child(2n) {
  height: 18px;
}
.voice-bars i:nth-child(3) {
  height: 13px;
}
.hello-bubble {
  position: absolute;
  top: 7px;
  right: 0;
  background: #f8bb72;
  border: 1px solid #353c34;
  border-radius: 18px 18px 3px 18px;
  padding: 15px 27px;
  font:
    italic 38px Georgia,
    serif;
  transform: rotate(8deg);
}
.hello-bubble span {
  display: block;
  font:
    10px system-ui,
    sans-serif;
  margin-top: 5px;
}
.art-spark {
  position: absolute;
  top: 3px;
  left: 6px;
  font-size: 69px;
  color: var(--orange);
  transform: rotate(14deg);
}
.book {
  width: 195px;
  position: absolute;
  bottom: 4px;
  right: -5px;
  transform: rotate(9deg);
}
.art-label {
  position: absolute;
  bottom: 17px;
  left: 30px;
  writing-mode: vertical-rl;
  font-size: 8px;
  letter-spacing: 2px;
}
.chapter-strip {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 50px;
  background: #f0e7da;
  border-block: 1px solid var(--line);
  padding: 21px 24px;
  font-size: 10px;
  letter-spacing: 1.6px;
  color: #625b50;
}
.chapter-strip > span:nth-child(even) {
  color: var(--orange);
  font-size: 22px;
}
.position-section,
.faq-section {
  max-width: 1248px;
  padding: 88px 24px;
  margin: auto;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 80px;
}
h2 {
  font-size: 35px;
  line-height: 1.5;
  letter-spacing: -1px;
  font-weight: 700;
  margin: 15px 0;
}
.section-intro > p:last-child,
.section-heading-row > p {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.9;
}
.opportunity-card {
  border: 1px solid #d8cbbc;
  padding: 30px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 5px 5px 0 #efe6d9;
}
.opportunity-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.role-icon {
  font:
    31px Georgia,
    serif;
  color: var(--orange);
  background: #fff1e2;
  border-radius: 10px;
  padding: 10px;
}
.role-label {
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 6px 12px;
  font-size: 10px;
}
h3 {
  font-size: 24px;
  font-weight: 650;
  margin-top: 23px;
}
.english-label {
  color: var(--muted);
  font-size: 11px;
  margin-top: 3px;
  letter-spacing: 1px;
}
.role-description {
  color: var(--muted);
  font-size: 13px;
  margin-top: 22px;
}
.role-facts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 22px;
}
.role-facts span {
  font-size: 10px;
  border-radius: 4px;
  padding: 6px 9px;
  background: #f8f4ed;
}
.inline-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-top: 25px;
  padding: 21px 0 0;
  border: 0;
  border-top: 1px solid var(--line);
  background: none;
  color: var(--orange);
  font-size: 13px;
  font-weight: 600;
}
.inline-action > span {
  font-size: 23px;
}
.process-section {
  padding: 72px max(24px, calc((100% - 1200px) / 2));
  background: #f7f1e8;
  border-block: 1px solid var(--line);
}
.section-heading-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}
.section-heading-row h2 {
  margin-bottom: 0;
}
.process-grid {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 0;
  margin: 40px 0 0;
  gap: 28px;
}
.process-grid li {
  border-top: 1px solid #cfc3b4;
  padding-top: 23px;
}
.step-number {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 36px;
  color: var(--orange);
  font-family: Georgia, serif;
}
.step-number > span {
  font-size: 25px;
}
.process-grid h3 {
  font-size: 20px;
  margin-top: 22px;
}
.process-grid p {
  font-size: 13px;
  color: var(--muted);
  margin-top: 13px;
  max-width: 300px;
}
.step-caption {
  display: block;
  font-size: 8px;
  letter-spacing: 1.2px;
  margin-top: 30px;
  color: #766656;
}
.faq-section {
  grid-template-columns: 1fr 1.5fr;
}
.faq-list details {
  border-bottom: 1px solid var(--line);
}
.faq-list details:first-child {
  border-top: 1px solid var(--line);
}
.faq-list summary {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 24px 0;
  list-style: none;
  font-size: 14px;
  font-weight: 550;
}
.faq-list summary::-webkit-details-marker {
  display: none;
}
.faq-plus {
  font-size: 22px;
  color: var(--orange);
  font-weight: 400;
}
.faq-list details[open] .faq-plus {
  transform: rotate(45deg);
}
.faq-list details p {
  padding: 0 28px 24px 0;
  color: var(--muted);
  font-size: 13px;
}
.closing {
  background: #304a40;
  color: #fff9ed;
  text-align: center;
  margin: 0 max(24px, calc((100% - 1200px) / 2));
  border-radius: 14px;
  padding: 52px 24px;
  position: relative;
}
.closing .eyebrow {
  color: #e5c9a4;
}
.closing h2 {
  font-size: 37px;
}
.closing > p:not(.eyebrow) {
  font-size: 13px;
  color: #d8e0d7;
  margin-bottom: 26px;
}
.closing .apply-button {
  background: #ffd496;
  border-color: #ffd496;
  color: #303c33;
}
.closing .apply-button:hover {
  background: #f5c580;
}
.closing-login {
  display: block;
  margin: 18px auto 0;
  padding: 7px;
  border: 0;
  background: none;
  color: #eee8dc;
  font-size: 11px;
}
.closing-spark {
  position: absolute;
  left: 6%;
  top: 30%;
  color: #d5a36b;
  font-size: 70px;
}
.home-footer {
  max-width: 1248px;
  margin: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 43px 24px;
}
.footer-wordmark {
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.8px;
}
.footer-wordmark > span {
  display: block;
  font-size: 9px;
  font-weight: 400;
  letter-spacing: 2px;
  margin-top: 5px;
}
.home-footer p {
  font-size: 11px;
}
.home-footer p > span {
  color: var(--muted);
  font-size: 10px;
}
.home-footer a {
  font-size: 11px;
}
section[id] {
  scroll-margin-top: 24px;
}
@media (max-width: 1000px) {
  .hero {
    gap: 20px;
    padding-block: 55px;
  }
  h1 {
    font-size: 39px;
  }
  .hero-art {
    height: 400px;
  }
  .lesson-card {
    left: 8px;
    right: 12px;
  }
  .lesson-board {
    padding-inline: 18px;
  }
  .board-line {
    right: 12px;
    width: 40px;
    height: 40px;
  }
  .book {
    width: 165px;
  }
  .position-section,
  .faq-section {
    gap: 45px;
  }
  .chapter-strip {
    gap: 26px;
  }
  .closing-spark {
    font-size: 45px;
  }
}
@media (max-width: 760px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 40px 24px 32px;
    gap: 16px;
  }
  .hero h1 {
    font-size: clamp(30px, 7.9vw, 46px);
    letter-spacing: -1px;
    margin-top: 19px;
  }
  .hero-intro {
    font-size: 13px;
  }
  .hero-actions {
    gap: 22px;
    margin-top: 25px;
  }
  .hero-note {
    margin-top: 22px;
    font-size: 10px;
  }
  .hero-art {
    height: 360px;
    max-width: 440px;
    width: 100%;
    margin-inline: auto;
  }
  .lesson-card {
    top: 65px;
    left: 9px;
    right: 17px;
  }
  .lesson-board strong {
    font-size: 33px;
  }
  .lesson-board {
    padding-block: 18px 22px;
  }
  .hello-bubble {
    top: 12px;
    right: 0;
    font-size: 30px;
    padding: 12px 22px;
  }
  .art-spark {
    top: 15px;
    font-size: 52px;
  }
  .book {
    width: 145px;
    bottom: -3px;
    right: -6px;
  }
  .art-label {
    bottom: 14px;
    left: 0;
  }
  .lesson-bottom {
    font-size: 6px;
  }
  .chapter-strip {
    gap: 18px;
    font-size: 8px;
    letter-spacing: 1px;
    padding: 13px 20px;
  }
  .chapter-strip > span:nth-child(n + 4) {
    display: none;
  }
  .position-section,
  .faq-section {
    grid-template-columns: 1fr;
    gap: 27px;
    padding: 48px 24px;
  }
  h2 {
    font-size: 28px;
  }
  .section-intro > p:last-child {
    font-size: 13px;
  }
  .opportunity-card {
    padding: 24px;
  }
  .role-description {
    font-size: 12px;
  }
  .role-facts {
    gap: 7px;
  }
  .role-facts span {
    font-size: 9px;
  }
  .process-section {
    padding: 44px 24px;
  }
  .section-heading-row {
    display: block;
  }
  .section-heading-row > p {
    font-size: 12px;
    margin-top: 18px;
  }
  .process-grid {
    grid-template-columns: 1fr;
    gap: 26px;
    margin-top: 28px;
  }
  .process-grid li {
    position: relative;
    padding-left: 52px;
    padding-top: 19px;
  }
  .step-number {
    position: absolute;
    left: 0;
    top: 17px;
    font-size: 26px;
  }
  .step-number > span {
    display: none;
  }
  .process-grid h3 {
    margin-top: 0;
    font-size: 18px;
  }
  .process-grid p {
    margin-top: 8px;
    font-size: 12px;
  }
  .step-caption {
    margin-top: 17px;
  }
  .faq-list summary {
    font-size: 13px;
    padding-block: 20px;
  }
  .faq-list details p {
    font-size: 12px;
  }
  .closing {
    margin-inline: 20px;
    padding: 38px 19px;
  }
  .closing h2 {
    font-size: 25px;
    letter-spacing: -0.8px;
  }
  .closing .eyebrow {
    font-size: 8px;
  }
  .closing > p:not(.eyebrow) {
    font-size: 11px;
  }
  .closing-spark {
    display: none;
  }
  .home-footer {
    padding: 32px 24px;
    flex-wrap: wrap;
    gap: 22px;
  }
  .home-footer p {
    font-size: 10px;
  }
  .home-footer a {
    margin-left: auto;
    font-size: 10px;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }
}
</style>
