-- Backup of user_permissions prior to FK fix at 20250912_054857 UTC
CREATE TABLE user_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(50), revoked_at DATETIME, revoked_by VARCHAR(100), expires_at DATETIME, is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES "users_legacy_backup" (id),
    FOREIGN KEY (permission_id) REFERENCES permissions (id),
    UNIQUE(user_id, permission_id)
);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (1, 2, 1, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (2, 2, 2, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (3, 2, 3, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (4, 2, 4, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (5, 2, 5, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (6, 2, 6, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (7, 2, 7, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (8, 2, 8, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (9, 2, 9, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (10, 2, 10, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (11, 2, 11, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
INSERT INTO user_permissions (id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) VALUES (12, 2, 12, '2025-08-29T22:40:04.366799', NULL, NULL, NULL, NULL, 1);
