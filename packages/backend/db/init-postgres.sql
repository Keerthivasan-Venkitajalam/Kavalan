-- Kavalan PostgreSQL Schema
-- Structured data: users, sessions, threat events, audit logs

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP,
    preferences JSONB,
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP
);

-- Sessions table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,  -- 'meet', 'zoom', 'teams'
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    max_threat_score DECIMAL(4,2),
    alert_count INTEGER DEFAULT 0,
    CONSTRAINT valid_platform CHECK (platform IN ('meet', 'zoom', 'teams'))
);

-- Threat events table
CREATE TABLE threat_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    threat_score DECIMAL(4,2) NOT NULL,
    audio_score DECIMAL(4,2),
    visual_score DECIMAL(4,2),
    liveness_score DECIMAL(4,2),
    threat_level VARCHAR(20) NOT NULL,
    is_alert BOOLEAN DEFAULT FALSE,
    confidence DECIMAL(3,2),
    CONSTRAINT valid_threat_level CHECK (threat_level IN ('low', 'moderate', 'high', 'critical')),
    CONSTRAINT valid_scores CHECK (
        threat_score >= 0 AND threat_score <= 10 AND
        (audio_score IS NULL OR (audio_score >= 0 AND audio_score <= 10)) AND
        (visual_score IS NULL OR (visual_score >= 0 AND visual_score <= 10)) AND
        (liveness_score IS NULL OR (liveness_score >= 0 AND liveness_score <= 10))
    )
);

-- Audit logs table (DPDP compliance)
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Indexes for performance
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_start_time ON sessions(start_time);
CREATE INDEX idx_threat_events_session ON threat_events(session_id);
CREATE INDEX idx_threat_events_timestamp ON threat_events(timestamp);
CREATE INDEX idx_threat_events_score ON threat_events(threat_score);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Insert default test user for development
INSERT INTO users (email, consent_given, consent_timestamp) 
VALUES ('test@kavalan.dev', TRUE, NOW());
