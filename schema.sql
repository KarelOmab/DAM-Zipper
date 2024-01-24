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
    message TEXT,
    FOREIGN KEY (request_id) REFERENCES requests (id)
);