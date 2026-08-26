# 网页端分 Skill 测试指南

每次修改模板后创建一个新工作区，避免旧工作区保留旧版 Skill。展开回复上方的 `Thinking & tool calls`，确认读取了预期 Skill，并检查工作区文件中的落盘结果。

## 准备一个全新测试工作区

1. 在 `inno-agent` 目录启动服务：

   ```powershell
   npm run server -- --home ./runtime --workspace ./workspace --port 3000
   ```

2. 保持服务窗口运行，在另一个 PowerShell 中进入同时包含 `inno-agent` 与 `adaptive-math-learning-agent` 的父目录，执行：

   ```powershell
   $body = @{ name = '数学 Agent 网页验收'; isTemp = $false } | ConvertTo-Json -Compress
   $bytes = [Text.Encoding]::UTF8.GetBytes($body)
   $ws = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/workspaces' -Method Post -ContentType 'application/json; charset=utf-8' -Body $bytes
   $target = Join-Path '.\inno-agent\workspace' $ws.relPath
   Get-ChildItem -LiteralPath '.\adaptive-math-learning-agent' -Force | Copy-Item -Destination $target -Recurse -Force
   $ws
   ```

3. 打开 `http://127.0.0.1:3000`，刷新页面，点击“新建对话”，选择已有工作区“数学 Agent 网页验收”。若页面在复制模板前已经创建过会话，请重新新建一个绑定该工作区的会话。
4. 在开始测试前，可在该工作区终端运行 `node scripts/validate-artifacts.mjs`；没有运行数据时也应通过。

若模板已作为本地 Hub Preset 被客户端加载，可直接在新建对话时选择“中小学数学错因诊断与自适应巩固”，无需手工复制。

## 1. 任务结构化与轨迹分析

发送：

```text
我是五年级学生。请诊断：1/2+1/3=2/5，因为分子相加、分母相加。不要直接确认稳定误区，每次只问一道题。
```

预期读取 `math-task-structurer`、`math-reasoning-trace-analyzer` 和 `math-misconception-verifier`，并生成 `attempts/*.json` 与 `misconception-ledger.md`。

还应检查：学生自述“分子相加、分母相加”被原样保存在 `verbatim_reasoning` 中；状态只能是 `observation`；回复只呈现一道探针，不出现“让我读取 Skill/正在写文件”等内部旁白。

## 2. 多表征修复

发送：

```text
我会列一次函数解析式，但看不懂表格和图像。请用一次只转换一种表征的方式帮我检查。
```

预期读取 `multi-representation-repair`，先给一个最小表格或对应关系任务，不一次展示整套答案。

## 3. 自适应练习和质量门

发送：

```text
请针对刚才已经验证的错因生成一题同构题。展示前先检查条件、答案和难度，但不要提前告诉我答案。
```

预期读取 `adaptive-math-practice`，在 `practice/*.json` 中保存目标、答案和全部质量检查；聊天中只出现题目。

运行 `node scripts/validate-artifacts.mjs`，确认五项质量门均为 `true`，且聊天回复没有泄露 `expected_answer`。

## 4. 几何边界

发送：

```text
两个三角形有两组对应边相等，所以它们一定全等。我的证明到这里结束，请检查。
```

预期使用 rubric，指出条件尚不足并提出一个最小反例探针，不把示意图外观当作条件。

## 5. 教师版报告

完成至少两轮作答后发送：

```text
请生成教师版阶段报告，所有关键结论必须引用真实 attempt_id 和 evidence_id，没有证据就写暂无证据。
```

预期读取 `math-learning-progress-reporter`，生成 `reports/*-teacher.md`，且不编造掌握率。

紧接着再请求一次同类报告，确认生成第二个带新时间或序号的文件，旧报告没有被覆盖。

## 6. 缺条件停止

发送：

```text
一个三角形两边长分别是3和5，求面积。
```

预期只说明缺少的信息，不给唯一面积、不记录虚假错误证据。

## 建议验收记录

每个场景保存三类证据：网页回复截图、展开后的 Skill/工具调用截图、对应 attempt/practice/report 文件。最终再运行：

```powershell
node scripts/validate-template.mjs
node scripts/validate-artifacts.mjs
```

运行时工作区目录名由平台生成，因此 `validate-template.mjs` 的“目录名必须等于 preset id”检查应在提交目录 `adaptive-math-learning-agent/` 中执行；运行工作区主要执行 `validate-artifacts.mjs`。
