--
--  upgrade_mysql_0.2-0.3.sql
--
--  Created by Ross Light on 5/4/08.
--

-- Upgrade user table
ALTER TABLE tg_user ADD COLUMN `image_uuid` CHAR(32);
ALTER TABLE tg_user ADD COLUMN `cell_number` CHAR(10);
ALTER TABLE tg_user ADD COLUMN `cell_provider` VARCHAR(16);

-- Upgrade many-to-many identity tables
ALTER TABLE user_group CHANGE COLUMN `tg_group_group_id` `group_id` INTEGER;
ALTER TABLE user_group CHANGE COLUMN `tg_user_user_id` `user_id` INTEGER;
ALTER TABLE group_permission CHANGE COLUMN `tg_group_group_id` `group_id` INTEGER;
ALTER TABLE group_permission CHANGE COLUMN `permission_permission_id` `permission_id` INTEGER;

-- Upgrade entry table
ALTER TABLE entries CHANGE COLUMN `killed_by` `killer_id` INTEGER;
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
