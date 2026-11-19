
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempts` (
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
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapters` (
  `id` varchar(36) NOT NULL,
  `subject_id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `order_num` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chapters_subject_id` (`subject_id`),
  CONSTRAINT `chapters_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(36) NOT NULL,
  `role` varchar(20) NOT NULL,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chat_messages_session_id_id` (`session_id`,`id`),
  CONSTRAINT `chat_messages_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_sessions` (
  `id` varchar(36) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `user_id` varchar(36) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_chat_sessions_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `error_analyses` (
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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_points` (
  `id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_knowledge_points_chapter_id` (`chapter_id`),
  CONSTRAINT `knowledge_points_ibfk_1` FOREIGN KEY (`chapter_id`) REFERENCES `chapters` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `material_chunks` (
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
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `materials` (
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
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `problems` (
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
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subjects` (
  `id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` varchar(36) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(200) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `variants` (
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
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wrong_book` (
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
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

