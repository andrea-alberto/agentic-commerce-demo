# Technical Documentation — UCP Travel Retail Demo Suite

> **Agentic Commerce: Redefining E-Commerce across UCP, Web MCP, and Physical Retail**  
> *GDG DevFest Milano 2026 Reference Implementation*

Welcome to the technical documentation hub for the **UCP Travel Retail Demo Suite**. This directory contains comprehensive architectural specifications, open protocol analyses, cryptographic models, and presentation flowcharts.

---

## 📚 Documentation Map

| Document | Primary Audience | Description |
| :--- | :--- | :--- |
| [**`architecture.md`**](architecture.md) | Architects & Developers | **Complete System Specification**: Nx monorepo topology, 4 Angular 22 frontends, 2 Python microservices, AP2 FIDO2 Passkey mandates, Web MCP server, RFC 9421 HTTP signatures, and physical retail BOPIS engine. |
| [**`gcp-ucp-architecture.md`**](gcp-ucp-architecture.md) | Cloud & Enterprise Architects | **Production Serverless Middleware on GCP**: Production blueprint featuring Google Cloud Run, Cloud Firestore, Vertex AI (Gemini 2.5 Flash), Cloud Armor, and API Gateway for enterprise merchant deployment. |
| [**`ucp-requirements-and-capabilities-matrix.md`**](ucp-requirements-and-capabilities-matrix.md) | Protocol Specialists & Auditors | **UCP Conformance Matrix**: RFC 2119 normative requirement analysis, relevance levels (1–3), and capability mapping against the official UCP standard. |
| [**`flows/agentic-commerce-flowcharts-v21.md`**](flows/agentic-commerce-flowcharts-v21.md) | Speakers & Presenters | **High-Legibility Slide Flowcharts**: Presentation-optimized Mermaid flowcharts (`flowchart LR`) comparing OpenAI ACP with Google UCP + AP2 across conversational, delegated, and physical retail flows. |
| [**`diagrams/`**](diagrams/README.md) | DevOps & Architects | **Diagrams as Code**: Python implementation utilizing the `diagrams` library with official Google Cloud Platform vector architecture icons. |
| [**`../TODO.md`**](../TODO.md) | Contributors & Maintainers | **Project Roadmap & Backlog**: Exhaustive list of planned enhancements (`TODO-01` to `TODO-12`), including the standalone `ucp-web-client`, Chrome Extension, and airport logistics. |

---

## 🎯 The 4 Live Demos at a Glance

The demo suite showcases a head-to-head architectural comparison of the four primary agentic commerce paradigms:

| # | Demo Scenario | Protocol Channel | Frontend App | Backend Services | Architectural Highlight |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Direct A2A** *(Baseline)* | JSON-RPC 2.0 / A2A | `chat-client` (`:4200`) | `backend-merchant` (`:10999`) | B2C conversational chatbot with Gemini 2.5 Flash, intent extraction, and AP2 Passkey payment modal. |
| **2** | **Web MCP** *(E-Commerce)* | Model Context Protocol | `storefront-webmcp` (`:4202`) | `backend-merchant` (`:10999`) | Browser-native shopping agent discovering and executing web tools (`filterProducts`, `addToCart`, `configureFulfillment`). |
| **3** | **Two-Agent Federation** *(Full A2A)* | Machine-to-Machine A2A | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longleftrightarrow$ `backend-merchant` (`:10999`) | Two autonomous AI agents negotiating: Personal Shopper injects travel context and coordinates with the Station Merchant. |
| **4** | **UCP Standard REST** *(REST Binding)* | HTTP REST + **RFC 9421** | `shopper-client` (`:4203`) | `backend-shopper` (`:10998`) $\longrightarrow$ `backend-merchant` (`:10999`) | Enterprise UCP checkout session with ECDSA-P256 HTTP Message Signatures and physical BOPIS dispatch. |

---

## 🗺️ Port Allocation & Service Map

All services run simultaneously without port conflicts:

| Port | Service Name | Stack | Primary Endpoint | Role in Architecture |
| :---: | :--- | :--- | :--- | :--- |
| **`4200`** | `chat-client` | Angular 22 Standalone | `http://localhost:4200` | Demo 1: Baseline Conversational A2A Interface |
| **`4201`** | `bopis-dashboard` | Angular 22 Standalone | `http://localhost:4201` | Station Dispatcher Hub (Kitchen, Barista, Platform Couriers) |
| **`4202`** | `storefront-webmcp` | Angular 22 Standalone | `http://localhost:4202` | Demo 2: Web Storefront with Web MCP Tool Registry |
| **`4203`** | `shopper-client` | Angular 22 Standalone | `http://localhost:4203` | Demo 3 & 4: Split-View Chat + Real-Time Protocol Inspector |
| **`10998`** | `backend-shopper` | Python / Starlette | `http://localhost:10998` | Personal Shopper Agent (SSE stream, traveler ticket context) |
| **`10999`** | `backend-merchant` | Python / Starlette | `http://localhost:10999` | Milan Central Merchant Hub (UCP REST, RFC 9421, Gemini 2.5) |

---

## 🚀 Quick Execution Guide

### Simultaneous Launch (All 6 Services)
```powershell
npm run serve:all
```

### Individual Execution via Nx
```powershell
# Backend Services
npx nx run backend-merchant:serve     # Port 10999
npx nx run backend-shopper:serve      # Port 10998

# Frontend Applications
npx nx run shopper-client:serve       # Port 4203 (Demo 3 & 4)
npx nx run bopis-dashboard:serve      # Port 4201 (Station Screen)
npx nx run storefront-webmcp:serve    # Port 4202 (Demo 2)
npx nx run chat-client:serve          # Port 4200 (Demo 1)
```

For test suite verification across MCP tools:
```powershell
npm run test:mcp
```
