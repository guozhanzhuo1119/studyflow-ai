-- 有意变更：旧库的 attempts 表连 client_token 列都没有，
-- 因此下面两条语句不是“迁移已有结构”，而是新增幂等键。
-- 历史行留 NULL；MySQL 唯一索引允许多个 NULL，不会互相冲突。
ALTER TABLE attempts ADD COLUMN client_token VARCHAR(64) NULL;
ALTER TABLE attempts ADD UNIQUE KEY uk_attempts_client_token (client_token);
