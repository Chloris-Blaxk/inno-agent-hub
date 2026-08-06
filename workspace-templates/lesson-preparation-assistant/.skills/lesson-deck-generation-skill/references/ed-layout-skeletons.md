# ED 版式 HTML 骨架

本文件给 Agent 提供可参照的 HTML 结构骨架。正式生成仍由 `scripts/render_lesson_deck.py` 输出；若手写或扩展模板，必须保持 `data-layout="EDxx"`、`data-slot` 和教师信息分离。

## 通用外壳

```html
<section class="slide layout-edxx layout-family" data-layout="EDxx" data-stage="stage" data-slot="slot_id" data-slot-ratio="16:9" data-asset-status="placeholder">
  <div class="slide-inner">
    <aside class="rail">...</aside>
    <div class="content">
      <div class="topbar" data-animate="fade">
        <div class="kicker">STAGE</div>
        <div class="stage-meta">教学意图短句</div>
      </div>
      <div class="main">...</div>
      <div class="footer">...</div>
    </div>
  </div>
</section>
```

学生屏幕只放 `screen` 内容。`teacherScript`、预设回应和反馈方式只能进入 JSON、speaker panel 或 PPTX notes。

## ED01 Studio Cover

```html
<div class="main" data-animate="rise">
  <div class="hero-copy">
    <h1 class="headline large">课题</h1>
    <p class="subtitle">年级学科 · 课型</p>
    <div class="outcome">本节课产出</div>
  </div>
  <div class="visual-mark visual-slot" data-slot="cover_mark" data-mark="MATH"></div>
</div>
```

## ED02 Lesson Journey

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">今天走五步</h2>
    <p class="subtitle">先知道要去哪里，课堂才不会迷路。</p>
  </div>
  <div class="panel journey-panel visual-slot" data-slot="journey_map">
    <div class="route">...</div>
  </div>
</div>
```

## ED03 Hook Scene

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">先判断再计算</h2>
    <p class="question">驱动问题</p>
  </div>
  <div class="visual-card hook-card visual-slot" data-slot="hook_visual" data-ratio="16:9">
    <div class="kicker">VISUAL SLOT</div>
    <p class="brief">情境图说明</p>
  </div>
</div>
```

## ED04 Inquiry Split

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">旧方法够用吗</h2>
    <p class="subtitle">讨论提示</p>
  </div>
  <div class="compare-grid visual-slot" data-slot="inquiry_workspace">
    <div class="compare-card">观点 A</div>
    <div class="compare-card">观点 B</div>
  </div>
</div>
```

## ED05 Concept Canvas

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">核心概念短句</h2>
    <p class="key-idea">可迁移的一句话</p>
    <ul class="bullet-list">...</ul>
  </div>
  <div class="visual-card concept-canvas visual-slot" data-slot="concept_diagram" data-ratio="16:10">
    <div class="kicker">DIAGRAM</div>
    <p class="brief">可编辑图示说明</p>
  </div>
</div>
```

## ED06 Board Model

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">板书模型</h2>
    <p class="subtitle">把方法留在黑板上。</p>
  </div>
  <div class="panel board-panel visual-slot" data-slot="board_model">
    <ul class="bullet-list">...</ul>
  </div>
</div>
```

## ED07 Example Flow

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">完整走一遍</h2>
    <p class="subtitle">典型例题</p>
  </div>
  <div class="panel step-panel visual-slot" data-slot="step_flow">
    <div class="step-list">...</div>
  </div>
</div>
```

## ED08 Practice Lab

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">先说方法再动笔</h2>
    <p class="subtitle">先说方法，再开始动笔。</p>
  </div>
  <div class="task-grid visual-slot" data-slot="practice_grid">...</div>
</div>
```

## ED09 Error Clinic

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">这个做法哪里不对</h2>
    <p class="subtitle">错误不是终点。</p>
  </div>
  <div class="error-stack visual-slot" data-slot="error_pair">
    <div class="error-box">错误想法</div>
    <div class="fix-box">修正方法</div>
    <div class="check-box">检查题</div>
  </div>
</div>
```

## ED10 Activity Studio

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">用证据说话</h2>
    <p class="subtitle">让学生留下可观察的课堂证据。</p>
  </div>
  <div class="activity-card visual-slot" data-slot="activity_workspace">
    <div class="task-title">学生动作</div>
    <p class="brief">材料或记录要求</p>
  </div>
</div>
```

## ED11 Summary Board

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">把方法带走</h2>
    <p class="subtitle">压缩成可复述句子。</p>
  </div>
  <div class="panel summary-panel visual-slot" data-slot="summary_board">
    <ul class="summary-list">...</ul>
  </div>
</div>
```

## ED12 Exit Ticket

```html
<div class="main">
  <div data-animate="rise">
    <h2 class="headline">两分钟出门测</h2>
    <p class="subtitle">用短测决定下一步教学。</p>
  </div>
  <div class="ticket-grid visual-slot" data-slot="exit_ticket">...</div>
</div>
```
