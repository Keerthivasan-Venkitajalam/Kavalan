// Kavalan MongoDB Schema
// Unstructured data: evidence, digital FIRs

db = db.getSiblingDB('kavalan');

// Evidence collection
db.createCollection('evidence', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['session_id', 'user_id', 'timestamp'],
      properties: {
        session_id: {
          bsonType: 'string',
          description: 'UUID of the session'
        },
        user_id: {
          bsonType: 'string',
          description: 'UUID of the user'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Timestamp of evidence capture'
        },
        audio: {
          bsonType: 'object',
          properties: {
            transcript: { bsonType: 'string' },
            language: { bsonType: 'string' },
            detected_keywords: { bsonType: 'object' },
            segments: { bsonType: 'array' }
          }
        },
        visual: {
          bsonType: 'object',
          properties: {
            frame_url: { bsonType: 'string' },
            analysis: { bsonType: 'string' },
            uniform_detected: { bsonType: 'bool' },
            badge_detected: { bsonType: 'bool' },
            threats: { bsonType: 'array' },
            text_detected: { bsonType: 'string' },
            confidence: { bsonType: 'double' }
          }
        },
        liveness: {
          bsonType: 'object',
          properties: {
            face_detected: { bsonType: 'bool' },
            blink_rate: { bsonType: 'double' },
            stress_level: { bsonType: 'double' },
            is_natural: { bsonType: 'bool' }
          }
        },
        metadata: {
          bsonType: 'object',
          properties: {
            platform: { bsonType: 'string' },
            browser: { bsonType: 'string' },
            extension_version: { bsonType: 'string' },
            encrypted: { bsonType: 'bool' },
            encryption_key_id: { bsonType: 'string' }
          }
        }
      }
    }
  }
});

// Digital FIR collection
db.createCollection('digital_fir', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['fir_id', 'session_id', 'user_id', 'generated_at'],
      properties: {
        fir_id: {
          bsonType: 'string',
          description: 'Unique FIR identifier'
        },
        session_id: {
          bsonType: 'string',
          description: 'UUID of the session'
        },
        user_id: {
          bsonType: 'string',
          description: 'UUID of the user'
        },
        generated_at: {
          bsonType: 'date',
          description: 'FIR generation timestamp'
        },
        summary: {
          bsonType: 'object',
          properties: {
            total_duration: { bsonType: 'int' },
            max_threat_score: { bsonType: 'double' },
            alert_count: { bsonType: 'int' },
            threat_categories: { bsonType: 'array' }
          }
        },
        evidence: {
          bsonType: 'object',
          properties: {
            transcripts: { bsonType: 'array' },
            frames: { bsonType: 'array' },
            threat_timeline: { bsonType: 'array' }
          }
        },
        legal: {
          bsonType: 'object',
          properties: {
            chain_of_custody: { bsonType: 'array' },
            cryptographic_signature: { bsonType: 'string' },
            hash: { bsonType: 'string' },
            retention_until: { bsonType: 'date' }
          }
        }
      }
    }
  }
});

// Create indexes for performance
db.evidence.createIndex({ session_id: 1 });
db.evidence.createIndex({ user_id: 1 });
db.evidence.createIndex({ timestamp: -1 });
db.evidence.createIndex({ 'metadata.platform': 1 });

db.digital_fir.createIndex({ fir_id: 1 }, { unique: true });
db.digital_fir.createIndex({ session_id: 1 });
db.digital_fir.createIndex({ user_id: 1 });
db.digital_fir.createIndex({ generated_at: -1 });

print('MongoDB collections and indexes created successfully');
