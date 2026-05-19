CREATE DATABASE IF NOT EXISTS qa_system DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE qa_system;

CREATE TABLE `user` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
                        `username` VARCHAR(30) NOT NULL UNIQUE COMMENT '用户名',
                        `password` VARCHAR(120) NOT NULL COMMENT '密码', -- 实际项目请存 BCrypt 密文
                        `nickname` VARCHAR(20) DEFAULT '用户' COMMENT '昵称',
                        `role` VARCHAR(20) DEFAULT 'USER' COMMENT '角色: SUPER_ADMIN, USER',
                        `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

CREATE TABLE `chat_session` (
                                `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                                `session_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '业务UUID',
                                `user_id` BIGINT NOT NULL,
                                `session_name` VARCHAR(50) DEFAULT '新会话',
                                `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话表';

-- 4. 对话历史表 (核心: 存问答记录)
CREATE TABLE `chat_history` (
                                `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                                `session_id` VARCHAR(100) NOT NULL,
                                `user_id` BIGINT NOT NULL,
                                `user_input` TEXT NOT NULL COMMENT '用户问题',
                                `llm_response` TEXT COMMENT 'AI回答',
                                `source` VARCHAR(20) COMMENT '来源: cache/llm',
                                `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (`session_id`) REFERENCES `chat_session`(`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话历史表';

-- 5. 知识库管理表 (业务端管理用，sync_status=0 表示还没推送到 Python)
CREATE TABLE `knowledge_base` (
                                  `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                                  `content` TEXT NOT NULL COMMENT '知识内容',
                                  `sync_status` TINYINT DEFAULT 0 COMMENT '0-未同步, 1-已同步',
                                  `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库源数据';

ALTER TABLE chat_history
    ADD COLUMN think_content LONGTEXT NULL COMMENT '模型思考内容';

