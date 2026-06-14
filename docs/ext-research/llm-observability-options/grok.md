**## Options**

### 1. OpenTelemetry (with opentelemetry-instrumentation-anthropic or manual spans)
- **What it is**: Open standard for distributed tracing, metrics, and logs. Open-source (Apache 2.0). Core SDK + contrib instrumentation; no SaaS required.
- **Integration effort**: Low for auto (one `instrument()` call + exporter setup); medium for manual spans in layered pipeline. 5-20 lines + exporter config. Add decorators or context managers for multi-agent/ReAct.
- **Anthropic API support**: Dedicated `opentelemetry-instrumentation-anthropic` auto-instruments SDK calls (prompts, responses, tokens, latency). Fallback to manual spans.
- **Storage backend**: OTLP exporter to any compatible backend (Jaeger, Tempo, Zipkin, self-hosted collector, or custom). Query via backend tools or Python OTEL APIs.
- **Kuzu/graph compatibility**: Export spans as custom events/attributes and ingest into Kuzu via Python client (map spans to nodes/edges: e.g., `PromptVersion` → `LLMCall` → `AgentRun`). Cypher queries possible on exported graph data.
- **Prompt-diff / prompt-version tracking**: Manual (attach `prompt_hash`, `version_id`, or full text diffs as span attributes/events). No built-in versioning UI.
- **Gaps**: No LLM-specific UI/dashboard out-of-box; requires backend setup. Less turnkey for cost accounting or prompt diffs. Parent-child spans excellent via context propagation.
- **Code sketch**:
```python
from opentelemetry import trace
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

AnthropicInstrumentor().instrument()  # auto for SDK
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("pipeline_run", attributes={"framework": "COSTAR+Persona"}) as span:
    # layered prompt build...
    with tracer.start_as_current_span("claude_call") as llm_span:
        resp = client.messages.create(...)  # auto-captured
        llm_span.set_attribute("prompt.layer", "ConstitutionalAI")
        # custom: span.set_attribute("prompt.version", hash_or_id)
```

### 2. OpenLLMetry (Traceloop)
- **What it is**: Open-source LLM extensions on top of OpenTelemetry. Apache 2.0 / open core.
- **Integration effort**: Very low — `Traceloop.init()` + imports. Auto-instruments pipeline layers via decorators if extended.
- **Anthropic API support**: Excellent native auto-instrumentation for Anthropic SDK (prompts, responses, tokens, latency, tools).
- **Storage backend**: OTEL-compatible (any exporter: Jaeger, Prometheus, or cloud). Full traces queryable via OTEL APIs or backend.
- **Kuzu/graph compatibility**: Same as OTEL — export spans and map to Kuzu nodes (strong fit for agent graphs alongside your domain graph).
- **Prompt-diff / prompt-version tracking**: Span attributes for layers/versions; manual diff logic. Good for structured metadata.
- **Gaps**: Still needs OTEL backend for UI/storage. Less polished prompt versioning than dedicated LLM tools. Watch for instrumentation overhead in tight ReAct loops.
- **Code sketch**:
```python
from traceloop.sdk import Traceloop
Traceloop.init(app_name="prompt-research", disable_batch=True)

@workflow(name="multi_agent_run")
def run_pipeline(run_id: str):
    # COSTAR + layers build prompt
    resp = client.messages.create(...)  # fully auto-traced with tokens/latency
    # attributes auto-populated + custom
```

### 3. Langfuse
- **What it is**: Open-source (AGPL/EE) + SaaS/self-hosted LLM observability platform. Strong Python SDK.
- **Integration effort**: Low-medium. OTEL-based Python SDK + `AnthropicInstrumentor` or `@observe` decorator. Few files.
- **Anthropic API support**: Strong via OTEL instrumentation or manual SDK. Captures full prompts/responses/tokens.
- **Storage backend**: Postgres-backed (self-hosted) or cloud. Query via Python SDK, UI, or API. Cypher-like via custom export.
- **Kuzu/graph compatibility**: Export traces to Kuzu (spans as graph events) or run alongside. SDK allows custom metadata push.
- **Prompt-diff / prompt-version tracking**: Excellent — built-in prompt management, versions, diffs, and comparisons across runs.
- **Gaps**: Self-hosted setup overhead; cloud costs for heavy use. Multi-agent tracing solid but may need extra `@observe` for deep ReAct.
- **Code sketch**:
```python
from langfuse import get_client
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

langfuse = get_client()
AnthropicInstrumentor().instrument()  # OTEL to Langfuse

@observe()  # or manual
def claude_call(prompt, layer):
    return client.messages.create(...)  # full capture + version tracking
```

### 4. Arize Phoenix
- **What it is**: Open-source AI observability (tracing + evals). Open-source core.
- **Integration effort**: Low — OpenInference auto-instrumentation + Phoenix server.
- **Anthropic API support**: Good auto-instrumentation for Anthropic SDK via OpenInference.
- **Storage backend**: Local/server DB + UI. OTEL-compatible export. Python query API.
- **Kuzu/graph compatibility**: Export traces to Kuzu; strong for agent graphs (nodes for agents/prompts).
- **Prompt-diff / prompt-version tracking**: Solid via traces + datasets for experiments/comparisons. Good for research iteration.
- **Gaps**: More eval-focused than pure tracing; self-hosting for full control. Less emphasis on raw cost accounting.
- **Code sketch**: Similar to OTEL + `openinference-instrumentation-anthropic`.

### 5. Helicone
- **What it is**: Open-source + SaaS LLM gateway/observability. Focused on proxy logging.
- **Integration effort**: Minimal — proxy base URL + headers (no SDK wrapping for basic use).
- **Anthropic API support**: Direct via proxy (baseURL change). Captures prompts, responses, tokens, costs.
- **Storage backend**: Helicone DB (cloud/self-hosted). Query via dashboard/API.
- **Kuzu/graph compatibility**: Export logs to Kuzu via API/webhooks. Not native graph.
- **Prompt-diff / prompt-version tracking**: Basic versioning via metadata; proxy logs allow diff scripts.
- **Gaps**: Proxy adds latency/hop; less deep for internal pipeline layers/multi-agent without extra SDK. No full parent-child traces easily.
- **Code sketch**:
```python
client = Anthropic(
    base_url="https://anthropic.helicone.ai",
    default_headers={"Helicone-Auth": f"Bearer {HELICONE_KEY}"}
)
# All calls proxied + logged
```

### 6. W&B Weave / MLflow
- **What it is**: Weave (W&B): Lightweight tracing toolkit (open-source core). MLflow: Experiment tracking with LLM tracing (open-source).
- **Integration effort**: Very low (`weave.init()` or `mlflow.anthropic.autolog()`).
- **Anthropic API support**: Both auto-track SDK calls (prompts, tokens, latency).
- **Storage backend**: W&B cloud/project or MLflow tracking server. Query via SDK.
- **Kuzu/graph compatibility**: Custom export possible; Weave/MLflow better for experiment logs than deep graphs.
- **Prompt-diff / prompt-version tracking**: Strong in Weave for evals/versions; MLflow for runs comparison.
- **Gaps**: More experiment/eval oriented than production tracing. Weave cloud-heavy; less flexible storage.

---

**## Ranked Recommendation**

**1. OpenLLMetry (on OpenTelemetry)** — Best fit. Zero-magic auto-instrumentation for Anthropic + full pipeline layers via workflows/decorators gives you prompts, tokens (incl. cache), latency, agent context, and perfect parent-child spans with minimal code. Export OTEL data to your Kuzu graph (map spans → nodes for versions/agents) or any backend while keeping everything queryable and self-hosted. Handles your layered framework and ReAct coordinator natively as extensions of OTEL semantic conventions. Add custom attributes for framework layers and prompt hashes for diffs. Production-grade, no vendor lock, and you control storage.

**2. Langfuse (OTEL-based)** — Close second if you want a polished UI with built-in prompt versioning/diffs out-of-the-box and easy self-host. Excellent for research iteration and traceable multi-step runs. Slightly higher setup than pure OpenLLMetry if avoiding any SaaS, but pairs beautifully with your Kuzu setup via exports. Use `@observe` for specialist agents.

**3. Arize Phoenix** — Strong for evals + tracing in a research context. Good Anthropic support and experiment comparison, but less lightweight for pure telemetry into a custom Kuzu backend compared to the OTEL stack. Use if heavy evaluation of prompt variants is primary.

Prioritize OpenLLMetry first: install, init, instrument, then wire custom span attributes for your COSTAR/Persona/Constitutional layers and run_id. You can ship production-grade telemetry today and evolve the Kuzu ingestion as a thin exporter layer. This keeps you in control as a senior engineer without fighting abstractions.
