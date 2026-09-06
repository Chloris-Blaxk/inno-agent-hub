---
name: email-sender
description: >-
  通过真实 SMTP 把邮件实际发送出去（而不仅是写出邮件文本）。凡是需要"把信息通过邮件送达他人"的场景都用本技能——群发通知、调课/停课/考试提醒、给某人或一组收件人写信、把整理好的内容用邮件发出等。即使用户没明说"发邮件"，只要意图是"通知 / 告知 / 寄给某人 / 发给大家"，也应触发本技能。触发词：发邮件、发送邮件、群发、通知学生/同学/家长、把…发给…、邮件提醒、寄信、email、send email、notify by email、mail this to。
category: 开发工具
subject: 其它
kind: 通用工具
---

# email-sender · 邮件发送技能

装上本技能后，agent 通过 `scripts/send-email.py` 具备**真正发送邮件**的能力——不再只是写出邮件文本，而是能把它发出去。脚本自包含、与具体工作区解耦；凭据存在用户家目录，配一次即可跨会话、跨工作区复用。

> `<SKILL_DIR>` 指本技能所在目录（`SKILL.md` 所在处）。执行命令时把相对路径解析成该目录下的绝对路径，如 `python <SKILL_DIR>/scripts/send-email.py ...`。
> 依赖：Python 3（标准库，无需额外安装）。

## 流程总览

发信请求分三步：先看配置好没有 → 没配就引导用户配一次 → 撰写、预览、确认、发送。之所以把"预览确认"独立成一步，是因为邮件一旦发出无法撤回，尤其群发；先让用户核对收件人和正文能避免误发。

## 第一步：自检配置

任何发信请求，先运行自检，判断 SMTP 是否已就绪：

```bash
python <SKILL_DIR>/scripts/send-email.py check
```

- `✅ 配置完整` → 跳到第三步。
- `⚠️ 配置不完整` → 进入第二步引导配置。

## 第二步：引导配置（仅未配置时）

目标是拿到三样东西并写入配置：**邮箱服务商、发件地址、客户端授权码**。

关键点：多数邮箱的 SMTP 登录用的不是网页登录密码，而是单独生成的"客户端授权码/应用专用密码"。用登录密码几乎必然报 `535 认证失败`，所以引导时要讲清这个区别。各邮箱的授权码获取步骤见 `references/providers.md`——按用户的邮箱类型读取对应条目再转述，不必让用户自己猜。

1. 问用户用哪家邮箱（预设：163 / 126 / qq / exmail / aliyun / feishu / gmail / outlook；其他邮箱改问 host/port/tls，参数见 references）。
2. 问发件邮箱地址。
3. 指引用户拿到授权码（步骤见 references）。**过程中不要把授权码回显到对话里。**
4. 写入配置（用 `--provider` 自动带出 host/port/tls，用户就不用记这些）：

```bash
python <SKILL_DIR>/scripts/send-email.py config set \
    --provider 163 --user teacher@163.com --password "<授权码>"
```

5. 验证账号与授权码（会真连一次 SMTP 登录，但不发信）：

```bash
python <SKILL_DIR>/scripts/send-email.py check --test
```

   失败时脚本会给出对应邮箱的授权码提示；对照 `references/providers.md` 的排查表帮用户修正后重试。

## 第三步：撰写、预览、确认、发送

1. **确定收件人与正文**。收件人来自用户提供的地址或名册，不要编造邮箱。正文写清"谁、什么事、何时、何地、要怎么做"，让收件人一眼看懂。
2. **先 dry-run 预览**（默认行为，不发信）：

```bash
python <SKILL_DIR>/scripts/send-email.py send \
    --to "a@x.com,b@y.com" --subject "【调课通知】数据结构" --body-file /tmp/notice.txt
```

3. **把预览完整展示给用户，问清是否发送。** 没得到明确确认就停在 dry-run，别自作主张发出。
4. **确认后加 `--send` 真正发送**：

```bash
python <SKILL_DIR>/scripts/send-email.py send \
    --to "a@x.com,b@y.com" --subject "【调课通知】数据结构" --body-file /tmp/notice.txt --send
```

5. 发送后脚本自动把记录追加到 `$INNO_HOME/email-send-log.md` 并回报结果；失败会给出排查提示（详见 references 的报错表）。

## 命令速查

| 命令 | 作用 |
|---|---|
| `check` / `check --test` | 自检配置 / 附带真连登录验证（不发信） |
| `config set --provider <名> --user <邮箱> --password <授权码>` | 写入配置 |
| `config show` / `config path` | 脱敏查看配置 / 打印配置路径 |
| `send --to --subject --body-file [--send]` | 预览（默认）/ 发送（加 --send） |

## 配置与安全

- 凭据文件：`$INNO_HOME/email.json`（默认 `~/.inno-agent/email.json`），写入时自动设为 600 权限。也可用环境变量 `SMTP_HOST/PORT/USER/PASS/FROM/TLS` 覆盖，或用 `INNO_EMAIL_CONFIG` 指定路径。
- 授权码等同密码：不要写进会被提交/分享的文件，不要在回复里回显；怀疑泄露就去邮箱设置里吊销授权码即可，无需改主密码。
- 默认 dry-run，只有显式 `--send` 才发信。群发前务必再确认一次收件人范围，避免误发或漏发。

## 更多参考

- `references/providers.md` —— 各邮箱 host/port/tls 参数、授权码获取步骤、SMTP 报错排查表。配置或发送出问题时读它。
