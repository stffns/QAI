-- Backup user_roles at 20250912_055551 UTC
CREATE TABLE user_roles (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, assigned_by VARCHAR(100), expires_at DATETIME, is_active BOOLEAN DEFAULT 1, assigned_at DATETIME, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT uq_user_role UNIQUE (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES "users_legacy_backup" (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);
INSERT INTO user_roles VALUES (1, 1, NULL, NULL, 1, '2025-09-08 08:14:36');
INSERT INTO user_roles VALUES (2, 4, NULL, NULL, 1, '2025-09-08 08:14:36');
