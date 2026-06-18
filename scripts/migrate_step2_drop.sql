-- ============================================================
-- 数据库迁移 步骤2：清除脏历史 + 删除空旧库
-- ============================================================
-- 执行（密码交互输入）：
--   mysql -u root -p < scripts/migrate_step2_drop.sql
--
-- 前置：步骤1 已执行并验证（vnpy_china 6表行数一致，vnpy_china_dev 已空0表）
-- 本步骤破坏性但低风险：旧库已空，脏历史已随步骤1备份
-- ============================================================

-- 1. 清除 equity_snapshot 脏历史（available_cash/market_value 错误的2条），
--    次日 18:30 由修复后的采集器重新正确采集
DELETE FROM vnpy_china.equity_snapshot;

-- 2. 删除空掉的旧库（0表，无数据损失）
DROP DATABASE vnpy_china_dev;

SELECT 'step2_done' AS status;
