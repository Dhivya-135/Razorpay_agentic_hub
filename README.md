<a name="readme-top"></a>

<div align="center">

# ⚡ Razorpay Agentic Payment Hub 

### AI-Powered Conversational Commerce & Payment Orchestration

**Live Link** : https://razorpay-agent-hub.onrender.com/

**An agentic AI assistant that understands user intent, recommends products or experiences,  
and orchestrates secure Razorpay payments through a bounded, explainable workflow.**

<br />

[![Buildathon](https://img.shields.io/badge/Buildathon-2026-blue?style=for-the-badge)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#)
[![Razorpay](https://img.shields.io/badge/Razorpay-Test%20Mode-0C2451?style=for-the-badge)](#)
[![AI Agent](https://img.shields.io/badge/AI-Agentic%20Workflow-purple?style=for-the-badge)](#)

<br />

**Built for an agentic commerce experience where conversation becomes action.**

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Agent Workflow](#-agent-workflow)
- [Safety & Guardrails](#-safety--guardrails)
- [Payment Flow](#-payment-flow)
- [Supported Use Cases](#-supported-use-cases)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Running the Application](#-running-the-application)
- [Example Interaction](#-example-interaction)
- [Why This Is Agentic](#-why-this-is-agentic)
- [Future Scope](#-future-scope)
- [Buildathon Highlights](#-buildathon-highlights)
- [License](#-license)

---

<div align="center">

### 🤖 AI Agent × 🛒 Recommendations × 💳 Razorpay

**Built for Buildathon Submission**

</div>

---

## 🚀 Overview

**Razorpay Agentic Payment Hub** is an AI-driven commerce assistant that lets users interact naturally with an AI agent to discover food, movies, and experiences and proceed directly to payment.

Instead of navigating multiple applications, the user simply tells the agent what they want.

The agent:

- 🧠 Understands natural-language requests
- 🔎 Searches relevant catalog data
- 🎯 Recommends suitable options
- ⚙️ Executes actions using bounded tools
- 💳 Creates Razorpay payment orders
- 🔐 Verifies payments securely
- 📋 Maintains an explainable execution flow

The system is designed around **agentic decision-making with controlled tool execution**.

---

## 💡 Key Features

### 🤖 AI Agent

- Natural-language interaction
- Intent-based routing
- ReAct-style reasoning and action flow
- Tool-based execution
- Context-aware option selection

### 🍔 Food Ordering

- Food recommendation workflow
- Merchant-aware processing
- Direct Razorpay checkout generation
- No unnecessary confirmation after selection

### 🎬 Movie Booking

- Movie catalog search
- PVR INOX-oriented booking flow
- Numbered movie/ticket selection
- Direct checkout after selection

### 💳 Razorpay Integration

- Razorpay Test Mode
- Server-side order creation
- Razorpay Checkout
- Payment signature verification
- Transaction safety limits

### 🛡️ Guardrails

- Maximum transaction limit
- Bounded agent authority
- Controlled tool execution
- No invented product IDs or prices
- Merchant consistency
- Payment verification before fulfillment

---

## 🏗️ System Architecture

![AI-driven Agentic Commerce Architecture](architecture.jpeg)

### Agent Execution Flow

```text
User Request
     │
     ▼
┌─────────────────────┐
│     AI Agent        │
│ Intent + Reasoning  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Tool Execution Layer│
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
 Food Catalog   Movie Catalog
     │           │
     └─────┬─────┘
           ▼
┌─────────────────────┐
│ Guardrail Validation│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Razorpay Test Mode  │
│ Order + Checkout    │
└──────────┬──────────┘
           │
           ▼
      Payment Verify
```

---

## 🧠 Explainable Agent Flow

```text
STEP 1 → USER_REQUEST
        ↓
STEP 2 → ITEM_RECOMMENDED
        ↓
STEP 3 → CROSS_SELL
        ↓
STEP 4 → GUARDRAIL_CHECK
        ↓
STEP 5 → RAZORPAY_CHECKOUT
        ↓
STEP 6 → PAYMENT_VERIFIED
```

This creates an **auditable agent workflow** instead of allowing the AI to perform unrestricted actions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | FastAPI |
| AI Agent | Sarvam AI |
| Database | SQLite |
| Payment | Razorpay |
| API | REST API |
| Runtime | Python |
| Server | Uvicorn |

---

## 📁 Project Structure

```text
razorpay-agentic-payment-hub/
│
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── tools.py
│   └── db.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── architecture.png
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd razorpay-agentic-payment-hub
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
SARVAM_API_KEY=your_sarvam_api_key

RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_secret
```

> ⚠️ Never expose `RAZORPAY_KEY_SECRET` in frontend code or commit `.env` to GitHub.

### 5. Start the application

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://localhost:8000
```

---

## 💳 Payment Flow

```text
User
  ↓
AI Recommendation
  ↓
Tool Execution
  ↓
Razorpay Order Creation
  ↓
Razorpay Checkout
  ↓
Payment
  ↓
Server-side Signature Verification
  ↓
Payment Confirmed
```

The application uses **Razorpay Test Mode** during development and demonstration.

---

## 🎯 Example Queries

```text
"Recommend a meal for me"

"I want paneer tikka"

"Find me a movie"

"Show movies available today"

"I want the second option"

"Create a Razorpay payment link for this"
```

The agent interprets the request and executes the appropriate workflow.

---

## 🛡️ Safety & Guardrails

The agent operates under bounded authority.

### Transaction Limit

```text
Maximum Transaction: ₹5,000
```

### Other Controls

- No fabricated catalog items
- No fabricated prices
- No fabricated IDs
- Latest user selection takes priority
- Merchant context is preserved
- Payment signatures are verified server-side
- Agent actions are restricted to defined tools

---

## 🏆 Why This Project?

Traditional commerce requires users to manually search, compare, select, and pay across different interfaces.

Our approach introduces an **agentic commerce layer** where the user communicates naturally while the AI handles the interaction and tool orchestration.

### From:

```text
Search → Compare → Select → Checkout → Pay
```

### To:

```text
Ask → AI Understands → AI Acts → Pay
```

This creates a faster and more conversational payment experience.

---
What issue I faced:

1. Food Ordering – Razorpay Checkout Issue

Issue: After selecting a food recommendation, the backend successfully created the Razorpay order, but the Razorpay Checkout window was not opening consistently.

Fix: Updated the frontend Razorpay integration to properly load and detect the Razorpay Checkout SDK, validate the order ID, key ID, amount, and currency, and trigger Razorpay.open() using the order details returned by the backend. Added fallback handling for cases where automatic checkout opening is blocked.

Result: Food selections now correctly connect to the real Razorpay payment flow instead of using a mock payment.

2. AI Response Duplication

Issue: The AI agent occasionally generated/repeated the same response multiple times for a single user request.

Fix: Improved the agent's conversation/state handling and response processing so that each user message is processed once and the generated response is handled only once by the frontend. Also separated food recommendation, selection, and checkout states to avoid repeated processing.

Result: The agent now provides a cleaner single response per request and maintains the correct conversation flow.

## 🔮 Future Scope

- Real-time Zomato / Swiggy integrations
- Real-time PVR INOX availability
- Multi-agent commerce workflows
- Voice-based ordering
- Personalized recommendations
- Order tracking
- Loyalty and rewards integration
- UPI-first agentic payments

---

## 👥 Buildathon Project

**Razorpay Agentic Payment Hub**

Built as an **AI-driven agentic commerce and payment orchestration system** demonstrating how AI agents can safely interact with commerce tools and payment infrastructure.

---

<div align="center">

### ⚡ AI understands.  
### 🧠 AI decides.  
### ⚙️ Tools execute.  
### 💳 Razorpay completes the payment.

**Built for Buildathon 🚀**

</div>
