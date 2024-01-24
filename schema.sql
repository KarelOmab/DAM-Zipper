DROP TABLE IF EXISTS requests;
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_ip TEXT,
    user_agent TEXT,
    method TEXT,
    request_url TEXT,
    response_status INTEGER
);

DROP TABLE IF EXISTS jobs;
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    message TEXT,
    status TEXT DEFAULT 'pending',
    start_time DATETIME,
    end_time DATETIME,
    FOREIGN KEY (request_id) REFERENCES requests (id)
);

DROP TABLE IF EXISTS events;
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    message TEXT,
    FOREIGN KEY (job_id) REFERENCES job_id (id)
);