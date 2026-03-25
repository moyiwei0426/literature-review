-- ARIS-Lit PostgreSQL Schema
-- Version: 001_initial
-- Description: Core tables for ARIS-Lit literature review pipeline

BEGIN;

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    project_id    VARCHAR(255) PRIMARY KEY,
    name          VARCHAR(500) NOT NULL,
    description   TEXT,
    owner         VARCHAR(255) NOT NULL DEFAULT 'default_user',
    status        VARCHAR(50)  NOT NULL DEFAULT 'active',
    research_question TEXT,
    target_venues TEXT[],
    max_papers    INTEGER       NOT NULL DEFAULT 100,
    paper_count   INTEGER       NOT NULL DEFAULT 0,
    stage         VARCHAR(50)  NOT NULL DEFAULT 'retrieval',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Papers (raw candidates before deduplication)
CREATE TABLE IF NOT EXISTS papers (
    paper_id    VARCHAR(255) PRIMARY KEY,
    source      VARCHAR(50)  NOT NULL,  -- openalex | arxiv | crossref
    title       TEXT,
    authors     TEXT[],
    year        INTEGER,
    venue       VARCHAR(500),
    doi         VARCHAR(255),
    arxiv_id    VARCHAR(100),
    url         TEXT,
    abstract    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Paper chunks (section splits from parsing)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    VARCHAR(255) PRIMARY KEY,
    paper_id    VARCHAR(255) NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    section     VARCHAR(255),
    text        TEXT,
    quality_score NUMERIC(5,4),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Paper profiles (extraction output)
CREATE TABLE IF NOT EXISTS profiles (
    paper_id        VARCHAR(255) PRIMARY KEY REFERENCES papers(paper_id) ON DELETE CASCADE,
    research_problem TEXT,
    problem_type    VARCHAR(100),
    domain          VARCHAR(255),
    language_scope  VARCHAR(100),
    method_summary  TEXT,
    method_family   TEXT[],
    datasets        TEXT[],
    tasks           TEXT[],
    metrics         TEXT[],
    baselines       TEXT[],
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Claims
CREATE TABLE IF NOT EXISTS claims (
    claim_id    VARCHAR(255) PRIMARY KEY,
    paper_id    VARCHAR(255) NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    claim_text  TEXT NOT NULL,
    claim_type  VARCHAR(100),
    confidence  NUMERIC(5,4),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Claim evidence links
CREATE TABLE IF NOT EXISTS claim_evidence_links (
    link_id     VARCHAR(255) PRIMARY KEY,
    claim_id    VARCHAR(255) NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    chunk_id    VARCHAR(255) NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    support_type VARCHAR(50),
    confidence  NUMERIC(5,4)
);

-- Gap sets (analysis output)
CREATE TABLE IF NOT EXISTS gap_sets (
    gap_set_id    VARCHAR(255) PRIMARY KEY,
    project_id    VARCHAR(255) REFERENCES projects(project_id) ON DELETE SET NULL,
    candidate_gaps JSONB,
    verified_gaps JSONB,
    scored_gaps   JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Drafts (writing output)
CREATE TABLE IF NOT EXISTS drafts (
    draft_id    VARCHAR(255) PRIMARY KEY,
    project_id  VARCHAR(255) REFERENCES projects(project_id) ON DELETE SET NULL,
    title       VARCHAR(500),
    outline     JSONB,
    sections    JSONB,
    bib_entries JSONB,
    tex         TEXT,
    compile_result JSONB,
    version     INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_papers_year      ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_venue     ON papers(venue);
CREATE INDEX IF NOT EXISTS idx_papers_doi        ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id  ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_chunks_paper_id  ON chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section   ON chunks(section);
CREATE INDEX IF NOT EXISTS idx_profiles_domain  ON profiles(domain);
CREATE INDEX IF NOT EXISTS idx_claims_paper_id  ON claims(paper_id);
CREATE INDEX IF NOT EXISTS idx_gap_sets_project ON gap_sets(project_id);
CREATE INDEX IF NOT EXISTS idx_drafts_project   ON drafts(project_id);

COMMIT;
