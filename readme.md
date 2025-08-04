# Marvin — Personal Memory Assistant

Marvin is a local-first, voice/text personal memory app (external brain) with semantic retrieval, built around an MCP-style agent.  
This repository contains the Cursor agent configuration (`marvin.cursor.yaml`) and acts as the core spec for the MVP.

## Key Features (MVP)
- Natural language input (voice or text) in Hebrew.
- Embedding-based semantic memory storage and retrieval.
- Chat-style interaction: store facts, query them, handle ambiguity, duplicates, and undo with confirmation.
- Fully local storage (no cloud sync in MVP).
- Modular AI agent (Marvin) with clear tool interfaces and observability.

## Files
- `marvin.cursor.yaml` — Cursor/MCP agent configuration defining architecture, tools, flows, and example I/O.
- (future) `app/` — React Native / Expo UI client to interact with Marvin.
- (future) `agent/` — Implementation of the embedding-backed store, intent classification, and dialog manager.

## Getting Started

### 1. Inspect / Load the Agent
- Open your Cursor workspace.
- The agent config `marvin.cursor.yaml` should be auto-detected. If not:
  - Restart Cursor.
  - Use the agent selector and load/point to this file manually.
- Ask Marvin to propose the minimal functional architecture (per the prompt) and wait for confirmation before proceeding.

### 2. Bootstrap Project Structure (suggested)
```bash
cd /Users/shaik/projects/marvin
mkdir -p app src agent
touch app/App.js
