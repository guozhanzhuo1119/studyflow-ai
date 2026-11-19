-- V1：完全复用旧库结构（schema/studyflow_ai.sql，13 张表），另建 ai_jobs。
-- 旧库已存在真实数据，因此所有语句必须是 CREATE TABLE IF NOT EXISTS，
-- 禁止 DROP / TRUNCATE / 修改已有列。Flyway 以 baseline-version=0 接入旧库：
-- 已存在的表保持不变，只有 ai_jobs 会被真正创建。

CREATE TABLE IF NOT EXISTS `subjects` (
  `id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `chapters` (
  `id` varchar(36) NOT NULL,
  `subject_id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `order_num` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chapters_subject_id` (`subject_id`),
  CONSTRAINT `chapters_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `knowledge_points` (
  `id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_knowledge_points_chapter_id` (`chapter_id`),
  CONSTRAINT `knowledge_points_ibfk_1` FOREIGN KEY (`chapter_id`) REFERENCES `chapters` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `problems` (
  `id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `source` varchar(100) DEFAULT NULL,
  `tags` varchar(200) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `knowledge_point_id` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `content` text COMMENT '题目正文 Markdown，可嵌入图片',
  `type` varchar(16) DEFAULT 'single',
  `options` text,
  `answer` varchar(8) DEFAULT NULL,
  `explanation` text,
  `difficulty` int DEFAULT '3',
  PRIMARY KEY (`id`),
  KEY `ix_problems_knowledge_point_id` (`knowledge_point_id`),
  CONSTRAINT `problems_ibfk_1` FOREIGN KEY (`knowledge_point_id`) REFERENCES `knowledge_points` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `variants` (
  `id` varchar(36) NOT NULL,
  `problem_id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `difficulty` varchar(20) DEFAULT NULL,
  `link` varchar(300) DEFAULT NULL,
  `reason` text,
  `origin` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `content` text COMMENT '题目正文 Markdown，可嵌入图片',
  PRIMARY KEY (`id`),
  KEY `ix_variants_problem_id` (`problem_id`),
  CONSTRAINT `variants_ibfk_1` FOREIGN KEY (`problem_id`) REFERENCES `problems` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `users` (
  `id` varchar(36) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(200) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `attempts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `target_type` varchar(20) NOT NULL,
  `target_id` varchar(36) NOT NULL,
  `result` varchar(20) NOT NULL,
  `duration_sec` int DEFAULT NULL,
  `error_reason` text,
  `source` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_attempts_target` (`target_type`,`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `wrong_book` (
  `id` int NOT NULL AUTO_INCREMENT,
  `target_type` varchar(20) NOT NULL,
  `target_id` varchar(36) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `wrong_count` int NOT NULL,
  `mastered` tinyint(1) NOT NULL,
  `last_wrong_at` datetime DEFAULT NULL,
  `mastered_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_wrong_book_target` (`target_type`,`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `error_analyses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `problem_id` varchar(36) NOT NULL COMMENT '关联 Problem.id，字符串非外键',
  `problem_title` varchar(200) NOT NULL,
  `topic` varchar(100) DEFAULT NULL,
  `mother_problem` varchar(200) DEFAULT NULL,
  `error_type` varchar(20) NOT NULL,
  `tag` varchar(20) DEFAULT NULL,
  `specific_behavior` varchar(200) NOT NULL,
  `first_break_point` varchar(20) NOT NULL,
  `decomposition_sentence` varchar(300) DEFAULT NULL,
  `remedy_status` varchar(20) NOT NULL,
  `remedy_action` varchar(300) DEFAULT NULL,
  `user_note` text,
  `reviewed` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `identify_latency_sec` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_error_analyses_problem_id` (`problem_id`),
  KEY `ix_error_analyses_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `materials` (
  `id` varchar(64) NOT NULL,
  `title` varchar(200) NOT NULL,
  `subject_id` varchar(64) DEFAULT NULL,
  `file_name` varchar(255) NOT NULL,
  `file_type` varchar(16) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `page_count` int DEFAULT NULL,
  `char_count` int DEFAULT NULL,
  `quality` varchar(16) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `subject_id` (`subject_id`),
  CONSTRAINT `materials_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `material_chunks` (
  `id` varchar(64) NOT NULL,
  `material_id` varchar(64) NOT NULL,
  `page_no` int DEFAULT NULL,
  `seq` int DEFAULT NULL,
  `content` text NOT NULL,
  `char_count` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_material_chunks_material_id` (`material_id`),
  CONSTRAINT `material_chunks_ibfk_1` FOREIGN KEY (`material_id`) REFERENCES `materials` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` varchar(36) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `user_id` varchar(36) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chat_sessions_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(36) NOT NULL,
  `role` varchar(20) NOT NULL,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chat_messages_session_id_id` (`session_id`,`id`),
  CONSTRAINT `chat_messages_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 唯一新增表：Java 的异步 AI 任务（P4 使用，本阶段只建表）。
CREATE TABLE IF NOT EXISTS `ai_jobs` (
  `id` varchar(36) NOT NULL,
  `type` varchar(32) NOT NULL,
  `status` varchar(20) NOT NULL,
  `request_json` longtext,
  `result_json` longtext,
  `error` text,
  `created_at` datetime NOT NULL,
  `finished_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ai_jobs_status_created_at` (`status`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
