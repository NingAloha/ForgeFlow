# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow is an experimental system for stabilizing software engineering semantics.

It is not a “universal AI coding agent”, nor is it a black-box tool that directly generates complete projects for users.

ForgeFlow currently focuses on the following problem:

```text
Vague user intent
→ structured artifact
→ iterative clarification
→ local validation
→ more stable engineering input
```

In other words, ForgeFlow tries to constrain AI from being “the one who directly writes code” into:

```text
a bounded artifact transformer
```

The core goal is not to make AI complete development in one step, but to make intermediate software engineering artifacts:

- explicit
- inspectable
- verifiable
- traceable
- progressively stable

---

## Current Status

ForgeFlow is still in an early prototype stage.

Currently implemented:

```text
llm/
  Minimal OpenAI-compatible LLM calling primitive
```

Currently validated flow:

```text
User input
→ LLM JSON output
→ JSON object
```

---

## Current Project Structure

```text
ForgeFlow/
├── llm/
│   ├── api.py
│   ├── llm_caller.py
│   └── prompts/
│       └── json_only_system.txt
│
├── README.md
└── README_EN.md
```

---

## LLM Primitive

The `llm/` module currently does only one thing:

```text
system_prompt + user_prompt
→ OpenAI-compatible Chat Completion API
→ JSON object
```

It does not handle:

- agent orchestration
- memory
- retries
- workflow
- schema semantics
- business logic
- tool calling
- code generation

Current core interface:

```python
call_llm_json(system_prompt: str, user_prompt: str) -> dict
```

This is only the low-level transport primitive of ForgeFlow.

---

## Usage

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install openai python-dotenv
```

Create a `.env` file in the project root:

```env
MODEL_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=your_api_key
MODEL_NAME=your_model_name
```

Run the LLM calling test:

```bash
.venv/bin/python -m llm.llm_caller
```

## Current Design Principles

### 1. Small primitives first

ForgeFlow does not currently pursue a complete architecture.

It prioritizes validating components that are:

```text
small
actually runnable
clearly bounded
incrementally composable
```

instead of prematurely building:

- runtime
- orchestrator
- plugin system
- provider abstraction
- agent framework

---

### 2. Artifacts over conversation history

ForgeFlow should not rely on free-form conversation history as its long-term state.

The current direction is:

```text
current artifact + user clarification
→ refined artifact
```

instead of:

```text
full chat history
→ re-guess the requirement
```

---

### 3. Prompts are artifacts

ForgeFlow treats prompts as semantic transformation rules, not temporary strings.

Therefore, prompts are stored under:

```text
llm/prompts/
sieves/prompts/
```

and versioned as project files.

---

### 4. JSON is not semantic stability

ForgeFlow does not assume that “the model returned JSON” means the system is stable.

It explicitly distinguishes:

```text
JSON object
≠
valid requirement artifact
```

That is why the Requirement Clarifier includes a local schema validator.

---

## Long-Term Direction

ForgeFlow may eventually evolve into a multi-layer semantic sieve system:

```text
User Intent
  ↓
Requirement Sieve
  ↓
Design Sieve
  ↓
Contract Sieve
  ↓
Test Sieve
  ↓
Implementation Sieve
  ↓
Verification Sieve
```

Each layer should:

- receive explicit artifacts
- check structural validity
- expose unresolved items
- mark inconsistencies
- output a more stable artifact

---

## Long-Term Core Objects

ForgeFlow may eventually include:

- `RequirementSpec`
- `ModuleContract`
- `ContractGraph`
- `TestSuite`
- `IntegrationTestSuite`
- `VerificationResult`
- `FailureReport`
- `Assumption`
- `Revision`

However, these objects will not be implemented prematurely.

They should only be introduced when the next sieve genuinely needs them.

---

## Explicit Non-Goals for Now

ForgeFlow currently does not do:

- automatic full code generation
- autonomous agent loops
- black-box runtime orchestration
- automatic retries
- automatic rollback
- automatic commits
- multi-provider abstraction
- complex workflow orchestration
- safety / compliance checks
- artifact persistence

These are not the core concerns of the current stage.

---

## Current Core Question

The most important question for ForgeFlow right now is not:

```text
Can AI automatically write code?
```

It is:

```text
Can vague software requirements be progressively stabilized
through a controlled semantic loop
into structurally valid, verifiable, and transferable artifacts?
```

If this does not hold, then Design, Contract, Test, and Implementation stages will not have a stable foundation.

---

## Current Milestones

Completed:

```text
LLM transport primitive
Requirement clarification sieve prototype
Validated requirement artifact schema
Single-question refinement loop
```

Possible next step:

```text
Requirement artifact
→ Design / Contract artifact
```

Before moving to the next layer, the Requirement Clarifier should continue to be observed for stability.
