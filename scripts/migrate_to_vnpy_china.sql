-- ============================================================
-- 数据库迁移 步骤1：vnpy_china_dev → vnpy_china（CREATE + GRANT + RENAME）
-- ============================================================
-- 执行（密码交互输入，不留痕）：
--   mysql -u root -p < scripts/migrate_to_vnpy_china.sql
--
-- 本步骤原子、可回滚：RENAME 一条语句搬 6 表，要么全成功要么全回滚。
-- 步骤2（DELETE 脏历史 + DROP 旧库）在 Claude 核对行数一致后单独执行。
-- 已备份：backup_vnpy_china_dev.sql（30.5MB）
-- ============================================================

-- 1. 创建目标库
CREATE DATABASE IF NOT EXISTS vnpy_china
  CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- 2. 授权 vnpy_dev 账号访问新库（保留该账号）
GRANT ALL PRIVILEGES ON vnpy_china.* TO 'vnpy_dev'@'localhost';
FLUSH PRIVILEGES;

-- 3. 跨库搬迁 6 张表（元数据操作，秒级完成，零丢失）
RENAME TABLE vnpy_china_dev.db_bar_data          TO vnpy_china.db_bar_data,
             vnpy_china_dev.db_capital_flow      TO vnpy_china.db_capital_flow,
             vnpy_china_dev.db_hk_connect_stocks TO vnpy_china.db_hk_connect_stocks,
             vnpy_china_dev.db_stock_info        TO vnpy_china.db_stock_info,
             vnpy_china_dev.equity_snapshot      TO vnpy_china.equity_snapshot,
             vnpy_china_dev.stock_industry       TO vnpy_china.stock_industry;

-- 执行后由 Claude 用 vnpy_dev 只读核对行数，一致则执行步骤2
SELECT 'step1_done' AS status;
