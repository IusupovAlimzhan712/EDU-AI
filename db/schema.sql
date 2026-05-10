-- =====================================================================
-- EduAI Database Schema (Phase 1 + Phase 2 weeks 2-4 tables)
--
-- Source: Section 4.6.1 Data Dictionary (FYP1 report)
--
-- Note: This file is the canonical reference for the database structure.
-- The actual schema is created by Flask-Migrate (Alembic migrations) so
-- you don't have to run this manually unless you prefer raw SQL setup.
--
-- Quick start:
--     mysql -u root -p
--     mysql> CREATE DATABASE eduai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--     mysql> exit
--     # then run migrations from the backend folder:
--     flask db upgrade
-- =====================================================================

CREATE DATABASE IF NOT EXISTS eduai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE eduai;

-- ---------- Student ----------
CREATE TABLE IF NOT EXISTS student (
    studentId        INT AUTO_INCREMENT PRIMARY KEY,
    email            VARCHAR(255) NOT NULL UNIQUE,
    passwordHash     VARCHAR(255) NOT NULL,
    fullName         VARCHAR(100) NOT NULL,
    formLevel        INT NOT NULL,
    registrationDate DATE NOT NULL DEFAULT (CURRENT_DATE),
    CONSTRAINT ck_student_form_level CHECK (formLevel IN (4, 5))
);

-- ---------- Session ----------
CREATE TABLE IF NOT EXISTS session (
    sessionId    VARCHAR(128) PRIMARY KEY,
    studentId    INT NOT NULL,
    createdAt    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lastActivity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    isActive     BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (studentId) REFERENCES student(studentId) ON DELETE CASCADE,
    INDEX idx_session_student (studentId)
);

-- ---------- LearningProgress ----------
CREATE TABLE IF NOT EXISTS learning_progress (
    progressId   INT AUTO_INCREMENT PRIMARY KEY,
    studentId    INT NOT NULL UNIQUE,
    lastUpdated  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (studentId) REFERENCES student(studentId) ON DELETE CASCADE
);

-- ---------- Chapter ----------
CREATE TABLE IF NOT EXISTS chapter (
    formLevel    INT NOT NULL,
    chapterId    INT NOT NULL,
    chapterName  VARCHAR(255) NOT NULL,
    PRIMARY KEY (formLevel, chapterId),
    CONSTRAINT ck_chapter_form_level CHECK (formLevel IN (4, 5)),
    CONSTRAINT ck_chapter_id_positive CHECK (chapterId >= 1)
);

-- ---------- Topic ----------
CREATE TABLE IF NOT EXISTS topic (
    topicId                   INT AUTO_INCREMENT PRIMARY KEY,
    formLevel                 INT NOT NULL,
    chapterId                 INT NOT NULL,
    topicName                 VARCHAR(255) NOT NULL,
    content                   TEXT NOT NULL,
    estimatedDurationMinutes  INT NULL,
    pdfReference              VARCHAR(500) NULL,
    UNIQUE KEY uq_topic_form_chapter_name (formLevel, chapterId, topicName),
    CONSTRAINT fk_topic_chapter FOREIGN KEY (formLevel, chapterId)
        REFERENCES chapter(formLevel, chapterId),
    CONSTRAINT ck_topic_form_level CHECK (formLevel IN (4, 5))
);

-- ---------- CompletedTopic (junction) ----------
CREATE TABLE IF NOT EXISTS completed_topic (
    progressId   INT NOT NULL,
    topicId      INT NOT NULL,
    completedAt  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (progressId, topicId),
    FOREIGN KEY (progressId) REFERENCES learning_progress(progressId) ON DELETE CASCADE,
    FOREIGN KEY (topicId) REFERENCES topic(topicId) ON DELETE CASCADE
);

-- ---------- BookmarkedTopic (junction) ----------
CREATE TABLE IF NOT EXISTS bookmarked_topic (
    progressId    INT NOT NULL,
    topicId       INT NOT NULL,
    bookmarkedAt  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (progressId, topicId),
    FOREIGN KEY (progressId) REFERENCES learning_progress(progressId) ON DELETE CASCADE,
    FOREIGN KEY (topicId) REFERENCES topic(topicId) ON DELETE CASCADE
);

-- ---------- PasswordResetToken (extension, not in original dictionary) ----------
CREATE TABLE IF NOT EXISTS password_reset_token (
    tokenId    INT AUTO_INCREMENT PRIMARY KEY,
    studentId  INT NOT NULL,
    tokenHash  VARCHAR(64) NOT NULL UNIQUE,
    expiresAt  DATETIME NOT NULL,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    createdAt  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studentId) REFERENCES student(studentId) ON DELETE CASCADE,
    INDEX idx_reset_token_student (studentId)
);
