---
name: postmortem-writing
description: 事故报告写作：时间线、根因、证据、动作、follow-ups
when_to_use: 故障处理完成后生成 Incident Report
tools: []
safety: 不追责、只记录事实
---

# Postmortem Writing

## 结构
1. 概览：incident_id / service / environment / window
2. Root Cause：一句话根因 + fault_type + confidence
3. Evidence：各 subagent 的结构化摘要（不贴原始日志）
4. Plan：todo 状态
5. Remediation：proposed / approved / rejected / executed
6. Verification：恢复证据
7. Follow-ups：监控、runbook、测试、架构改进

## 写作规则
- blameless：描述系统行为，不指责个人
- 区分“时间相关”与“因果”
- 被拒绝的动作也要记录，并附安全替代方案
- 未知就写 unknown，禁止编造
