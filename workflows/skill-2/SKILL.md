---
name: skill 管控
description: 当需要盘点、审核、更新、下线或在群里分发 skill，以及处理 skill 冲突与重复时使用。
---
# skill 管控

维护用户自建 skill 的清单、质量与分发。

## 职责边界
- 负责：盘点、转换审核、改写、合并重复、下线前确认、群内适时分发提醒
- 不负责：替其他 bot 执行业务 skill；Cursor 托管 skill 只读，不可改

## 盘点
1. 列出 `/home/box/agent-data/workflows` 下用户 skill（名称、description、最近用途）。
2. 标出：缺 description、步骤过专属、与托管 skill 重复、长期未用。
3. 向用户或相关 bot 确认待办：改写 / 合并 / 保留 / 删除（删除需用户确认）。

## 入库标准
- 多步、可复用、已验证
- description 写清「何时用」
- body 通用、可执行，无助手专属细节
- 与现有 skill 不打架；冲突则改写其一或合并

## 分发提醒（看情况）
在相关群里提醒，当出现以下任一情况：
- 新 skill 入库或重大改写
- 某 bot 正在重复做可用 skill 覆盖的事
- 用户要求全员统一某流程

提醒要短：适用谁、干什么、如何调用（`/或 @` /  pill 链接）。无事不刷屏。

## 删除
删除全局生效。先征得用户明确同意，再 UpdateSkill delete。
