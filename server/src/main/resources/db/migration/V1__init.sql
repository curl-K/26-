-- 账号、试剂、会话、存取、告警、采样。告警和采样不挂在存取链上。
-- 演示账号：manager/manager123，chen/chen123，li/li123。

CREATE TABLE account (
    id bigserial PRIMARY KEY,
    username varchar(64) NOT NULL UNIQUE,
    display_name varchar(64) NOT NULL,
    role varchar(16) NOT NULL CHECK (role IN ('manager', 'taker')),
    password_hash varchar(100) NOT NULL,
    failed_attempts integer NOT NULL DEFAULT 0,
    locked_until timestamp,
    created_at timestamp NOT NULL
);

CREATE TABLE reagent (
    id bigserial PRIMARY KEY,
    chip_uid varchar(64) UNIQUE,
    name varchar(128) NOT NULL,
    level varchar(16) NOT NULL CHECK (level IN ('low', 'mid', 'high')),
    slot_no integer NOT NULL CHECK (slot_no IN (1, 2)),
    status varchar(32) NOT NULL CHECK (status IN ('pending', 'in_cabinet', 'taken_out')),
    updated_at timestamp NOT NULL
);

CREATE TABLE cabinet_session (
    id bigserial PRIMARY KEY,
    slot_no integer NOT NULL CHECK (slot_no IN (1, 2)),
    state varchar(16) NOT NULL CHECK (state IN ('waiting', 'open', 'closed')),
    first_account_id bigint,
    second_account_id bigint,
    first_name varchar(64),
    second_name varchar(64),
    started_at timestamp,
    opened_at timestamp,
    expires_at timestamp,
    closed_at timestamp,
    close_reason varchar(32),
    last_reading varchar(64),
    streak integer NOT NULL DEFAULT 0,
    present_uids varchar(512) NOT NULL DEFAULT '',
    removed_uids varchar(512) NOT NULL DEFAULT '',
    ignored_uids varchar(512) NOT NULL DEFAULT '',
    suppressed boolean NOT NULL DEFAULT false,
    dual_alarm boolean NOT NULL DEFAULT false
);

CREATE INDEX cabinet_session_slot_idx ON cabinet_session (slot_no, state);

CREATE TABLE access_record (
    id bigserial PRIMARY KEY,
    session_id bigint NOT NULL REFERENCES cabinet_session (id),
    reagent_id bigint NOT NULL REFERENCES reagent (id),
    chip_uid varchar(64),
    slot_no integer NOT NULL,
    action varchar(16) NOT NULL CHECK (action IN ('bind', 'return', 'take')),
    handler1 varchar(64),
    handler2 varchar(64),
    occurred_at timestamp NOT NULL
);

CREATE INDEX access_record_reagent_idx ON access_record (reagent_id, occurred_at DESC, id DESC);
CREATE INDEX access_record_session_idx ON access_record (session_id, id);

CREATE TABLE alarm (
    id bigserial PRIMARY KEY,
    alarm_type varchar(32) NOT NULL,
    chip_uid varchar(64),
    slot_no integer,
    message varchar(256) NOT NULL,
    session_id bigint,
    acknowledged boolean NOT NULL DEFAULT false,
    acknowledged_by bigint,
    acknowledged_at timestamp,
    created_at timestamp NOT NULL
);

CREATE TABLE sample (
    id bigserial PRIMARY KEY,
    device_name varchar(64) NOT NULL,
    slot_no integer,
    temperature double precision,
    humidity double precision,
    tvoc integer,
    eco2 integer,
    sampled_at timestamp NOT NULL
);

CREATE INDEX sample_time_idx ON sample (sampled_at DESC);

CREATE TABLE device_state (
    id integer PRIMARY KEY,
    last_seq integer NOT NULL,
    last_heartbeat timestamp
);

INSERT INTO device_state (id, last_seq) VALUES (1, 0);

INSERT INTO account (username, display_name, role, password_hash, failed_attempts, created_at) VALUES
('manager', '管理人', 'manager', '$2b$10$OJBF/eEhXeWaLgRXVcqvTOujR3HpthX32q.leOO9xIoY6XOQ0A7R6', 0, TIMESTAMP '2026-11-17 08:00:00'),
('chen', '陈', 'taker', '$2b$10$aBRFccvi1DqUr8fPhcqCCOhbNLpaDfL5moF8PslixS02g/2JvVlze', 0, TIMESTAMP '2026-11-17 08:00:00'),
('li', '李', 'taker', '$2b$10$W1jEOUfrcyr0moc6vH1uYOW3PgwMnG3ZQtS89cp/G6LiTb.5P0QTu', 0, TIMESTAMP '2026-11-17 08:00:00');
