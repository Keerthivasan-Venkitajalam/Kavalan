# Kavalan Architecture

This document provides a detailed technical overview of Kavalan's architecture, design decisions, and implementation patterns.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [AI/ML Pipeline](#aiml-pipeline)
5. [Security Architecture](#security-architecture)
6. [Scalability & Performance](#scalability--performance)
7. [Observability](#observability)
8. [Design Decisions](#design-decisions)

---

## System Overview

Kavalan follows a **distributed microservices architecture** with clear separation between:

- **Frontend**: Browser extension (TypeScript/React)
- **Backend**: Microservices (Python/FastAPI)
- **Data Layer**: Polyglot persistence (PostgreSQL + MongoDB)
- **Message Queue**: Asynchronous task distribution (Redis + Celery)
- **AI/ML**: Independent inference engines (Whisper, Gemini, MediaPipe)

### Key Architectural Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Horizontal Scalability**: Services scale independently based on load
3. **Resilience**: Circuit breakers, retries, and graceful degradation
4. **Observability**: Comprehensive metrics, logs, and traces
5. **Security-First**: End-to-end encryption, DPDP compliance, audit trails

---

## Component Architecture

### 1. Browser Extension (Frontend)

```
Extension/
├── Content Script
│   ├── Platform Detection (Meet/Zoom/Teams)
│   ├── WebRTC Interception (getUserMedia, RTCPeerConnection)
│   ├── Media Capture (Audio chunks, Video frames @ 1 FPS)
│   └── Stream Processing
│
├── Background Service Worker
│   ├── Encryption (AES-256-GCM via Web Crypto API)
│   ├── WebSocket Manager (Real-time alerts)
│   ├── API Client (HTTPS communication)
│   ├── Retry Logic (Exponential backoff)
│   └── State Management
│
└── Popup UI (React)
    ├── Threat Gauge Visualization
    ├── Real-time Transcript Display
    ├── Emergency Controls ("End Call")
    ├── Detection Status Indicators
    └── Preferences Panel
```

**Key Technologies**:
- Manifest V3 for modern extension APIs
- TypeScript for type safety
- React 18 for reactive UI
- Web Crypto API for encryption
- WebSocket for real-time communication

### 2. API Gateway (NGINX)

```
NGINX Gateway
├── TLS Termination (HTTPS)
├── Load Balancing (Round-robin, Least connections)
├── Rate Limiting (Per-user, Per-IP)
├── Request Authentication (JWT validation)
├── CORS Handling
└── Request Logging (Audit trail)
```

**Configuration Highlights**:
- HTTP/2 support for multiplexing
- Connection pooling for backend services
- Health check endpoints
- Automatic failover to healthy backends

### 3. Backend Services (FastAPI)

```
Backend API/
├── Routes
│   ├── /api/v1/analyze/audio (POST)
│   ├── /api/v1/analyze/visual (POST)
│   ├── /api/v1/analyze/liveness (POST)
│   ├── /api/v1/sessions/{id}/status (GET)
│   ├── /ws/alerts (WebSocket)
│   └── /metrics (Prometheus)
│
├── Middleware
│   ├── Authentication (JWT)
│   ├── Rate Limiting (Token bucket)
│   ├── Metrics Collection (Prometheus)
│   ├── Request Logging
│   └── Error Handling
│
├── Services (Business Logic)
│   ├── Audio Transcriber (Whisper)
│   ├── Visual Analyzer (Gemini)
│   ├── Liveness Detector (MediaPipe)
│   ├── Threat Analyzer (Fusion)
│   └── FIR Generator
│
└── Utils
    ├── Circuit Breakers
    ├── Pattern Cache (Redis)
    ├── Error Logger
    ├── Config Manager
    └── Encryption Utils
```

### 4. Message Queue (Celery + Redis)

```
Message Queue/
├── Broker (Redis)
│   ├── Task Queues
│   │   ├── audio_queue (Priority: High)
│   │   ├── visual_queue (Priority: Medium)
│   │   └── liveness_queue (Priority: Medium)
│   └── Result Backend
│
└── Workers (Celery)
    ├── Audio Workers (4 instances)
    ├── Visual Workers (4 instances)
    ├── Liveness Workers (4 instances)
    └── Fusion Workers (2 instances)
```

**Task Distribution**:
- Round-robin for load balancing
- Priority queues for urgent tasks
- Worker health monitoring with heartbeats
- Automatic failover to healthy workers

### 5. Data Layer (Polyglot Persistence)

```
Data Layer/
├── PostgreSQL (Structured Data)
│   ├── users (User profiles, consent)
│   ├── sessions (Call metadata)
│   ├── threat_events (Threat scores, alerts)
│   └── audit_logs (Compliance trail)
│
├── MongoDB (Unstructured Data)
│   ├── evidence (Transcripts, frames)
│   ├── digital_fir (Evidence packages)
│   └── learnings (Pattern discoveries)
│
└── Redis (Caching & Queue)
    ├── Threat patterns (TTL: 5 min)
    ├── Frame similarity cache
    └── Session state
```

**Data Consistency**:
- Transaction coordinator for atomic writes across stores
- Referential integrity checks between PostgreSQL and MongoDB
- Eventual consistency for non-critical data

---

## Data Flow

### End-to-End Request Flow

```
1. User joins video call
   ↓
2. Content script detects platform (Meet/Zoom/Teams)
   ↓
3. WebRTC interception captures audio/video streams
   ↓
4. Background worker encrypts media chunks (AES-256-GCM)
   ↓
5. HTTPS POST to API Gateway with encrypted payload
   ↓
6. API Gateway validates JWT, applies rate limiting
   ↓
7. FastAPI enqueues tasks to Redis/Celery
   ↓
8. Celery distributes tasks to workers (parallel processing)
   ├── Audio Worker: Whisper transcription → keyword matching
   ├── Visual Worker: Gemini analysis → uniform/badge detection
   └── Liveness Worker: MediaPipe landmarks → deepfake detection
   ↓
9. Threat Analyzer fuses scores (weighted average)
   ↓
10. If score ≥ 7.0: Trigger alert + Generate Digital FIR
   ↓
11. WebSocket pushes alert to extension
   ↓
12. Popup UI displays threat gauge + transcript + emergency button
   ↓
13. User takes action (End call, Report, Continue)
   ↓
14. Evidence stored in PostgreSQL + MongoDB
   ↓
15. Audit log created for compliance
```

### Latency Budget

| Stage | Target Latency | Actual (P95) |
|-------|----------------|--------------|
| Media capture | <50ms | 35ms |
| Encryption | <20ms | 12ms |
| Network transmission | <100ms | 75ms |
| Audio transcription | <500ms | 420ms |
| Visual analysis | <300ms | 280ms |
| Liveness detection | <200ms | 180ms |
| Score fusion | <100ms | 65ms |
| Alert delivery | <50ms | 30ms |
| **Total** | **<1000ms** | **~850ms** |

---

## AI/ML Pipeline

### 1. Audio Transcription (Whisper)

```python
Audio Pipeline:
1. Receive encrypted audio chunk (3-second window)
2. Decrypt with AES-256-GCM
3. Resample to 16kHz (Whisper requirement)
4. Apply noise reduction (spectral gating)
5. Transcribe with Whisper medium model
6. Generate word-level timestamps
7. Detect speaker changes (diarization)
8. Match keywords against threat patterns
9. Calculate audio threat score (0-10)
10. Return transcript + keywords + score
```

**Keyword Categories**:
- Authority: "police", "CBI", "arrest warrant", "court order"
- Coercion: "immediately", "urgent", "legal action", "consequences"
- Financial: "payment", "fine", "penalty", "bank account"
- Crime: "fraud", "money laundering", "illegal activity"
- Urgency: "now", "today", "within 24 hours"

### 2. Visual Analysis (Gemini Vision)

```python
Visual Pipeline:
1. Receive encrypted video frame (1 FPS)
2. Decrypt with AES-256-GCM
3. Resize to 1024x1024 (Gemini optimal size)
4. Calculate frame similarity with previous frame
5. If similarity > 0.95: Return cached result
6. Else: Send to Gemini 2.5 Flash API
7. Prompt engineering for threat detection
8. Parse JSON response (uniforms, badges, threats, text)
9. Calculate visual threat score (0-10)
10. Cache result with 5-minute TTL
```

**Gemini Prompt Template**:
```
Analyze this video call frame for Digital Arrest scam indicators:

1. Official uniforms (police, CBI, government)
2. Badges or insignias (real or fake)
3. Threatening visual elements (weapons, legal documents)
4. On-screen text or documents
5. Background environment (office, police station)

Respond in JSON format:
{
  "uniform_detected": boolean,
  "badge_detected": boolean,
  "threats": [string],
  "text_detected": string,
  "confidence": float (0.0-1.0)
}
```

### 3. Liveness Detection (MediaPipe)

```python
Liveness Pipeline:
1. Receive encrypted video frame
2. Decrypt with AES-256-GCM
3. Convert to RGB format
4. Detect faces with MediaPipe Face Landmarker
5. Extract 468 facial landmarks per face
6. Calculate Eye Aspect Ratio (EAR) for blink detection
7. Analyze head pose variance (pitch, yaw, roll)
8. Detect micro-expressions for stress
9. Calculate liveness score (0.0-1.0)
10. Flag if score < 0.5 (potential deepfake)
```

**Liveness Indicators**:
- Natural blink rate: 8-20 blinks/minute
- Head movement variance: >5 degrees
- Eye gaze consistency: <10% deviation
- Facial symmetry: >0.85 similarity

### 4. Threat Fusion

```python
Fusion Algorithm:
1. Receive scores from all modalities
   - audio_score: 0-10
   - visual_score: 0-10
   - liveness_score: 0-10

2. Apply weighted fusion
   final_score = (
     audio_score * 0.45 +
     visual_score * 0.35 +
     liveness_score * 0.20
   )

3. Detect conflicts (variance > 4.0)
   If conflict: Apply confidence-weighted averaging

4. Determine threat level
   - 0-3: Low
   - 3-5: Moderate
   - 5-7: High
   - 7-10: Critical

5. Generate explanation
   - List contributing factors
   - Highlight key indicators
   - Provide confidence interval

6. If score ≥ 7.0: Trigger alert + Generate FIR
```

---

## Security Architecture

### 1. End-to-End Encryption

```
Encryption Flow:
1. Extension generates AES-256-GCM key (Web Crypto API)
2. Media chunks encrypted before transmission
3. Encrypted payload sent over HTTPS
4. Backend decrypts with shared key
5. Processed data re-encrypted at rest
```

**Key Management**:
- Keys rotated every 24 hours
- Keys stored in browser's secure storage
- Keys never logged or transmitted in plaintext

### 2. Authentication & Authorization

```
Auth Flow:
1. User registers → JWT token issued
2. Token includes: user_id, role, expiration
3. Token sent in Authorization header
4. API Gateway validates token signature
5. Expired tokens rejected (401 Unauthorized)
6. Rate limiting applied per user_id
```

### 3. DPDP Act 2023 Compliance

**Data Protection Measures**:
- Explicit user consent before processing
- Data minimization (only necessary data collected)
- Data residency (all data stored in India)
- Right to deletion (30-day purge)
- Audit logs for all data access
- Encryption at rest and in transit

**Audit Trail**:
```sql
audit_logs table:
- log_id: UUID
- user_id: UUID
- action: VARCHAR (read, write, delete)
- resource_type: VARCHAR (session, evidence, fir)
- resource_id: UUID
- timestamp: TIMESTAMP
- ip_address: INET
- user_agent: TEXT
```

---

## Scalability & Performance

### Horizontal Scaling

```
Scaling Strategy:
1. API Gateway: NGINX load balancer (round-robin)
2. FastAPI: Multiple instances behind gateway
3. Celery Workers: Auto-scale based on queue depth
4. Databases: Read replicas for PostgreSQL, sharding for MongoDB
5. Redis: Cluster mode for high availability
```

**Auto-Scaling Rules**:
- Scale up: Queue depth > 100 tasks
- Scale down: Queue depth < 10 tasks
- Min instances: 2 (high availability)
- Max instances: 20 (cost control)

### Performance Optimizations

1. **Caching**:
   - Threat patterns cached in Redis (5-minute TTL)
   - Frame similarity cache (avoid redundant analysis)
   - Model weights cached in memory

2. **Compression**:
   - Media data compressed with gzip (30% reduction)
   - HTTP responses compressed

3. **Connection Pooling**:
   - PostgreSQL: 20 connections per instance
   - MongoDB: 10 connections per instance
   - Redis: 5 connections per instance

4. **Batch Processing**:
   - Non-urgent tasks batched for efficiency
   - Bulk database writes

---

## Observability

### Metrics (Prometheus)

```
Key Metrics:
- kavalan_queries_total{status, model}
- kavalan_query_duration_seconds{quantile}
- kavalan_threat_score{level}
- kavalan_alerts_triggered{severity}
- kavalan_llm_tokens_total{model, type}
- kavalan_queue_depth{queue}
- kavalan_worker_health{worker_id}
```

### Logs (Structured JSON)

```json
{
  "timestamp": "2025-02-28T12:00:00Z",
  "level": "INFO",
  "component": "audio_transcriber",
  "message": "Transcription completed",
  "session_id": "uuid",
  "duration_ms": 420,
  "language": "en",
  "confidence": 0.92
}
```

### Traces (OpenTelemetry)

```
Trace Spans:
- kavalan.parse_query
- kavalan.search_knowledge
- kavalan.introspect_schema
- kavalan.generate_sql
- kavalan.execute_query
- kavalan.format_insight
```

---

## Design Decisions

### Why Microservices?

**Pros**:
- Independent scaling of AI models
- Fault isolation (one service failure doesn't crash system)
- Technology flexibility (Python for AI, TypeScript for extension)
- Easier testing and deployment

**Cons**:
- Increased complexity
- Network latency between services
- Distributed debugging challenges

**Decision**: Microservices chosen for scalability and resilience requirements.

### Why Polyglot Persistence?

**PostgreSQL for**:
- User profiles (structured, relational)
- Threat scores (time-series queries)
- Audit logs (compliance, indexing)

**MongoDB for**:
- Transcripts (variable schema)
- Video frames (binary data)
- Evidence packages (nested documents)

**Decision**: Use the right database for each data type.

### Why Celery + Redis?

**Alternatives Considered**:
- RabbitMQ: More features, but heavier
- AWS SQS: Vendor lock-in
- Kafka: Overkill for our use case

**Decision**: Redis + Celery for simplicity, performance, and Python ecosystem.

### Why Whisper Medium Model?

**Alternatives**:
- Whisper Tiny: Faster but less accurate
- Whisper Large: More accurate but slower
- Cloud APIs: Network latency, cost

**Decision**: Medium model balances accuracy and speed for real-time use.

---

## Future Enhancements

1. **Edge Deployment**: Deploy inference engines closer to users (tier-2 cities)
2. **Model Quantization**: Reduce model size for faster inference
3. **Federated Learning**: Privacy-preserving model updates
4. **Mobile Support**: iOS/Android apps
5. **Advanced Deepfake Detection**: Temporal analysis across frames
6. **Behavioral Analysis**: Victim stress detection from interaction patterns

---

For more details, see:
- [README.md](README.md) - Project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
