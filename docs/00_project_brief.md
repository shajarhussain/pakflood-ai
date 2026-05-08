# PakFlood AI — Project Brief

## Mission

Build PakFlood AI: an AI-powered Pakistan flood intelligence and early-risk visualization dashboard. MVP focuses on floods; architecture supports future hazard modules.

## Problem Statement

Pakistan experiences repeated flood disasters from monsoon rainfall, river overflow, glacier-related hazards, and drainage limitations. Flood intelligence is fragmented across many sources, formats, and update speeds.

**Goal:** Build a cloud-based AI geospatial decision-support system that helps users understand current and predicted flood risk across Pakistan using satellite data, river forecasts, AI explanations, and source-backed confidence scores.

## Product Name & Tagline

**PakFlood AI** — AI-powered flood intelligence and early-risk visualization for Pakistan.

## Core User Story

> As a user, I open the Pakistan map, select a district, and the system shows current flood risk, causes, historical events, nearby rivers, rainfall anomaly, satellite evidence, linked reports, and AI-suggested actions with confidence and official-source warnings.

## Non-Negotiables

1. Flood logic lives only in `backend/app/hazards/flood/`
2. Every external source uses an Adapter class
3. Every ML model stores version, features, metrics, artifact path
4. Every risk explanation includes confidence, data freshness, sources, disclaimer
5. Never describe AI output as an official government warning
6. Tests pass before moving to the next phase

## Phases

| Phase | Name | Goal |
|---|---|---|
| 0 | Scaffold | Repository, docs, Docker, test runners |
| 1 | Visual MVP | Map UI with mock data |
| 2 | Backend | FastAPI + PostGIS + seed data |
| 3 | Adapters | Real data sources + source registry |
| 4 | ML Baseline | RandomForest/XGBoost model |
| 5 | AI Explanation | Source-backed structured explanations |
| 6 | Hardening | Testing, deployment, final docs |

## Safety

This is an educational decision-support prototype. It must always direct users to official PMD, FFD, NDMA, and PDMA warnings for real emergency decisions.
