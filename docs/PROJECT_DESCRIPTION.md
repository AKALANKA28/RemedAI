# Project Description

**Title:** RemedAI - Local Multi-Agent Tender Qualification System for Environmental Remediation Projects

## Industry field

Environmental engineering / public procurement / hazardous-site remediation.

## Specific problem

Small and mid-sized engineering firms receive dense public procurement packages that must be screened quickly. The hard part is not reading the tender; it is identifying whether the company truly qualifies, what evidence is missing, how risky the delivery plan would be, and whether bidding is commercially responsible.

## Why this is a strong CTSE problem

- It is a **complex, multi-step problem**, not a chatbot prompt.
- It naturally needs **multiple agents with distinct responsibilities**.
- It requires **real tools**: file ingestion, database lookup, schedule/risk computation, and artifact writing.
- It benefits from **strict state management** because every downstream agent depends on verified upstream outputs.
- It is privacy-sensitive in practice, which makes **local Ollama execution** a meaningful architectural choice.
- It demonstrates multi-model agent design by assigning different local SLMs to different jobs: Gemma for orchestration, Qwen for intake, Llama for compliance, Mistral for risk, and Phi for planning.

## Business value

RemedAI reduces wasted bid effort, highlights compliance gaps before legal review, and creates a defensible bid/no-bid decision trail that managers can inspect.
