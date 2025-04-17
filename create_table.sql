-- Drop the existing table if it exists
DROP TABLE IF EXISTS jobs;

-- Create the jobs table with appropriate data types
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    -- Basic job information
    job_id TEXT UNIQUE,
    title TEXT,
    company_name TEXT,
    company_url TEXT,
    location TEXT,
    job_url TEXT,
    apply_url TEXT,
    apply_type TEXT,
    
    -- Job details
    experience_level TEXT,
    sector TEXT,
    work_type TEXT,
    contract_type TEXT,
    salary TEXT,
    benefits TEXT,
    
    -- Application information
    applications_count TEXT,
    description TEXT,
    description_html TEXT,
    
    -- Company information
    company_id TEXT,
    poster_profile_url TEXT,
    poster_full_name TEXT,
    
    -- Dates
    published_at DATE,
    posted_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Analysis fields
    is_best_fit BOOLEAN DEFAULT FALSE,
    gpt_analysis TEXT,
    score NUMERIC(4,1)
);

-- Create indexes for better query performance
CREATE INDEX idx_job_title ON jobs(title);
CREATE INDEX idx_company_name ON jobs(company_name);
CREATE INDEX idx_location ON jobs(location);
CREATE INDEX idx_published_at ON jobs(published_at);
CREATE INDEX idx_is_best_fit ON jobs(is_best_fit);
CREATE INDEX idx_score ON jobs(score); 