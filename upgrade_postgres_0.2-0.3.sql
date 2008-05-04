--
--  upgrade_postgres_0.2-0.3.sql
--
--  Created by Ross Light on 5/4/08.
--

-- Upgrade user table
ALTER TABLE tg_user ADD COLUMN `image_uuid` CHAR(32);
ALTER TABLE tg_user ADD COLUMN `cell_number` CHAR(10);
ALTER TABLE tg_user ADD COLUMN `cell_provider` VARCHAR(16);

-- Upgrade many-to-many identity tables
ALTER TABLE user_group RENAME COLUMN `tg_group_group_id` TO `group_id`;
ALTER TABLE user_group RENAME COLUMN `tg_user_user_id` TO `user_id`;
ALTER TABLE group_permission RENAME COLUMN `tg_group_group_id` TO `group_id`;
ALTER TABLE group_permission RENAME COLUMN `permission_permission_id` TO `permission_id`;

-- Upgrade entry table
ALTER TABLE entries RENAME COLUMN `killed_by` TO `killer_id`;
ALTER TABLE tg_user ADD COLUMN `notify_sms` BOOLEAN;

-- Upgrade game table
ALTER TABLE game ADD COLUMN `human_undead_time` INTEGER;

-- Add new permissions
INSERT INTO permission (`permission_name`, `description`)
VALUES ('edit-entry', 'Edit Player Info'),
       ('send-mail', 'Use site email system');
INSERT INTO group_permission (`group_id`, `permission_id`)
VALUES ((SELECT `group_id` FROM tg_group WHERE group_name = 'admin'),
        (SELECT `permission_id` FROM permission WHERE permission_name = 'edit-entry')),
       ((SELECT `group_id` FROM tg_group WHERE group_name = 'admin'),
        (SELECT `permission_id` FROM permission WHERE permission_name = 'send-mail'));
