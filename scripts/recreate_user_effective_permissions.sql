DROP VIEW IF EXISTS user_effective_permissions;
CREATE VIEW user_effective_permissions AS
SELECT DISTINCT 
    u.id AS user_id,
    u.username,
    p.id AS permission_id,
    p.name AS permission_name,
    p.category,
    p.resource_type,
    p.action,
    "role" AS source_type,
    r.name AS source_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id AND rp.is_active = 1
JOIN permissions p ON rp.permission_id = p.id
UNION
SELECT DISTINCT
    u.id AS user_id,
    u.username,
    p.id AS permission_id,
    p.name AS permission_name,
    p.category,
    p.resource_type,
    p.action,
    "direct" AS source_type,
    "user_permission" AS source_name
FROM users u
JOIN user_permissions up ON u.id = up.user_id AND up.is_active = 1
JOIN permissions p ON up.permission_id = p.id;
