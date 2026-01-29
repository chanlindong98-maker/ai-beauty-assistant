-- ====================================================
-- 魅丽健康助手 - 数据库补全脚本 (v2)
-- 解决后台统计、配置和兑换码功能不可用的问题
-- ====================================================
-- 请在 Supabase Dashboard → SQL Editor 中运行此脚本
-- ====================================================

-- 1. 创建订单表 (用于营收统计)
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    out_trade_no TEXT UNIQUE NOT NULL, -- 商户订单号
    alipay_trade_no TEXT,              -- 支付宝交易号
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,    -- 支付金额
    credits_to_add INTEGER NOT NULL,   -- 获得的魔法值
    status TEXT DEFAULT 'PENDING',     -- 状态: PENDING, PAID, CANCELLED
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 创建系统配置表 (用于后台动态调整参数)
CREATE TABLE IF NOT EXISTS public.system_config (
    key TEXT PRIMARY KEY,             -- 配置键
    value TEXT NOT NULL,               -- 配置值
    description TEXT,                  -- 配置描述
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 创建兑换码记录表 (用于防止重复兑换)
CREATE TABLE IF NOT EXISTS public.used_redeem_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    credits_added INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 开启 RLS (安全策略)
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.used_redeem_codes ENABLE ROW LEVEL SECURITY;

-- 允许管理员视角 (Service Role) 访问所有数据
CREATE POLICY "Service role has full access to orders" ON public.orders FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access to config" ON public.system_config FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access to redeem_codes" ON public.used_redeem_codes FOR ALL USING (auth.role() = 'service_role');

-- 用户可以查看自己的订单
CREATE POLICY "Users can view own orders" ON public.orders FOR SELECT USING (auth.uid() = user_id);

-- 5. 添加自动更新触发器 (可选)
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON public.system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
