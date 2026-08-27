-- database/schema.sql
-- DecisionLens SQLite Schema
-- Simplified, normalized schema for storing Investigation Reports

-- Reference tables (dimension tables)
CREATE TABLE IF NOT EXISTS stores (
    store_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL
);

-- Core investigation tables
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'superstore',
    investigation_date TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    metric TEXT NOT NULL DEFAULT 'Revenue',
    current_value REAL,
    baseline_value REAL,
    confidence_score REAL NOT NULL,
    evidence_coverage TEXT NOT NULL,
    coverage_count INTEGER NOT NULL,
    total_analyzers INTEGER NOT NULL DEFAULT 8,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    analyzer_name TEXT NOT NULL,
    analyzer_score REAL,
    sufficient_data INTEGER NOT NULL,
    description TEXT,
    rank INTEGER,
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_investigations_store ON investigations(store_id);
CREATE INDEX IF NOT EXISTS idx_investigations_category ON investigations(category_id);
CREATE INDEX IF NOT EXISTS idx_investigations_confidence ON investigations(confidence_score);
CREATE INDEX IF NOT EXISTS idx_investigations_year_week ON investigations(year, week);
CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence(investigation_id);

-- Recommendations table (Phase 6)
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,  -- "immediate" | "short-term" | "monitor"
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

CREATE INDEX IF NOT EXISTS idx_recommendations_investigation ON recommendations(investigation_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_priority ON recommendations(priority);

-- Business Summaries table (Phase 7 — Gemini narration layer)
CREATE TABLE IF NOT EXISTS summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    generated_by TEXT NOT NULL DEFAULT 'gemini',  -- "gemini" | "template_fallback"
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

CREATE INDEX IF NOT EXISTS idx_summaries_investigation ON summaries(investigation_id);