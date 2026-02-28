# Changelog

All notable changes to Kavalan will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-28

### 🏆 Hackathon Release

**2nd Prize Winner** at GenAI Hackathon ML.Cbe 2025 organized by AI Tamil Nadu with Nunnari Labs, DeepWeaver.ai, and Google for Developers.

### Added

#### Browser Extension
- ✅ Chrome/Firefox extension with Manifest V3
- ✅ WebRTC stream interception for Google Meet, Zoom, Microsoft Teams
- ✅ Platform detection and automatic monitoring activation
- ✅ AES-256-GCM encryption for media transmission
- ✅ React-based popup UI with threat gauge visualization
- ✅ Real-time transcript display
- ✅ Emergency "End Call" button
- ✅ User preferences storage (language, alert volume, stealth mode)
- ✅ Multi-language support (Hindi, English, Tamil, Telugu, Malayalam, Kannada)

#### Backend Services
- ✅ FastAPI application with async endpoints
- ✅ NGINX API Gateway with TLS termination and load balancing
- ✅ JWT authentication middleware
- ✅ Rate limiting (per-user and per-IP)
- ✅ WebSocket endpoint for real-time alerts
- ✅ Celery + Redis message queue for task distribution
- ✅ Worker health monitoring and automatic failover
- ✅ Exponential backoff retry logic

#### AI/ML Inference Engines
- ✅ Audio transcription with OpenAI Whisper (medium model)
- ✅ Speaker diarization for multi-participant calls
- ✅ Keyword matching for scam pattern detection
- ✅ Visual analysis with Google Gemini 2.5 Flash Vision API
- ✅ Uniform and badge detection
- ✅ OCR for on-screen text extraction
- ✅ Liveness detection with MediaPipe Face Landmarker
- ✅ Deepfake detection via blink rate and head pose analysis
- ✅ Stress indicator identification

#### Threat Fusion & Alerting
- ✅ Weighted score fusion (Audio 45%, Visual 35%, Liveness 20%)
- ✅ Confidence-weighted conflict resolution
- ✅ Unified threat score (0-10 scale)
- ✅ Threat level classification (low/moderate/high/critical)
- ✅ Explainable AI with human-readable threat descriptions
- ✅ Threat score history tracking

#### Digital FIR Generation
- ✅ Automatic evidence collection when threat score ≥ 7.0
- ✅ Timestamped audio transcripts with speaker labels
- ✅ Video frame snapshots with annotations
- ✅ Unified threat scores with confidence intervals
- ✅ Cryptographic signatures for tamper-proofing
- ✅ Chain-of-custody tracking
- ✅ PDF export for legal submission

#### Database Layer
- ✅ PostgreSQL for structured data (users, sessions, threat events, audit logs)
- ✅ MongoDB for unstructured data (transcripts, frames, evidence packages)
- ✅ Transaction coordinator for atomic writes across polyglot stores
- ✅ Referential integrity checks between databases
- ✅ Audit logging for DPDP Act 2023 compliance

#### Error Handling & Resilience
- ✅ Circuit breakers for external APIs (Whisper, Gemini, MediaPipe)
- ✅ Database operation queueing on failure
- ✅ Comprehensive error logging with structured JSON format
- ✅ Graceful degradation with partial modality processing

#### Performance Optimization
- ✅ Redis caching for threat patterns (5-minute TTL)
- ✅ Frame deduplication (similarity > 0.95)
- ✅ Media compression (30% size reduction)
- ✅ Connection pooling for databases

#### Configuration Management
- ✅ Environment-based configuration (dev, staging, production)
- ✅ Configuration validation at startup
- ✅ Sensitive config encryption (AES-256)

#### Observability & Monitoring
- ✅ Prometheus metrics exporters
- ✅ Grafana dashboards (threat detection, system health, service performance)
- ✅ OpenTelemetry distributed tracing
- ✅ Structured logging with context

#### CI/CD Pipeline
- ✅ GitHub Actions workflows (CI and CD)
- ✅ Automated testing (unit, property-based, integration, E2E)
- ✅ 80% code coverage enforcement
- ✅ Blue-green deployment strategy
- ✅ Automatic rollback on failure
- ✅ Smoke tests post-deployment

#### Testing
- ✅ 45+ property-based tests validating correctness properties
- ✅ Unit tests for all core components
- ✅ Integration tests for extension-backend communication
- ✅ E2E tests for complete threat detection flow
- ✅ Parallel processing validation

### Security
- ✅ End-to-end encryption (AES-256-GCM)
- ✅ DPDP Act 2023 compliance
- ✅ Data residency (all data stored in India)
- ✅ Explicit user consent before processing
- ✅ Right to deletion (30-day purge)
- ✅ Audit trails for all data access

### Performance
- ✅ Sub-second latency (<1000ms end-to-end)
- ✅ Audio transcription: <500ms
- ✅ Visual analysis: <300ms
- ✅ Liveness detection: <200ms
- ✅ Score fusion: <100ms

### Documentation
- ✅ Comprehensive README with setup instructions
- ✅ Architecture documentation
- ✅ Contributing guidelines
- ✅ API documentation (FastAPI auto-generated)
- ✅ Configuration guide
- ✅ Deployment guide (Docker + Kubernetes)

---

## [Unreleased]

### Planned Features

#### Phase 2: Enhanced Detection (Q2 2025)
- [ ] Advanced deepfake detection with temporal analysis
- [ ] Behavioral pattern recognition (victim stress indicators)
- [ ] Network analysis (call origin, IP geolocation)
- [ ] Integration with law enforcement databases

#### Phase 3: Scale & Optimize (Q3 2025)
- [ ] Edge deployment in tier-2 Indian cities
- [ ] Model quantization for faster inference
- [ ] Federated learning for privacy-preserving improvements
- [ ] Mobile app for iOS/Android

#### Phase 4: Ecosystem (Q4 2025)
- [ ] API for third-party integrations
- [ ] White-label solution for enterprises
- [ ] Community reporting platform
- [ ] Educational resources and awareness campaigns

---

## Version History

### [1.0.0] - 2025-02-28
- Initial release for GenAI Hackathon ML.Cbe 2025
- Production-ready browser extension with multimodal AI threat detection
- Comprehensive backend microservices architecture
- DPDP Act 2023 compliant with full audit trails

---

## Contributors

**Team Thudakkam**:
- Keerthivasan S V ([@Keerthivasan-Venkitajalam](https://github.com/Keerthivasan-Venkitajalam))
- Naveen Babu M S ([@naveen-astra](https://github.com/naveen-astra))
- B Rahul ([@Bat-hub-hash](https://github.com/Bat-hub-hash))

---

For more details on each release, see the [GitHub Releases](https://github.com/Keerthivasan-Venkitajalam/Kavalan/releases) page.
