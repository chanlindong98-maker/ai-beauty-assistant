-- ====================================================
-- 魅丽健康助手 - Supabase 数据库初始化脚本
-- ====================================================
-- 请在 Supabase Dashboard → SQL Editor 中执行此脚本
-- ====================================================

-- 1. 创建用户资料表
-- 存储用户的扩展信息（Supabase Auth 自动管理 auth.users）
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nickname TEXT NOT NULL,
    device_id TEXT NOT NULL,
    credits INTEGER DEFAULT 3 CHECK (credits >= 0),
    referrals_today INTEGER DEFAULT 0 CHECK (referrals_today >= 0),
    last_referral_date DATE DEFAULT CURRENT_DATE,
    referrer_id UUID REFERENCES public.user_profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 创建使用记录表（可选，用于数据分析）
CREATE TABLE IF NOT EXISTS public.usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    feature_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 为 user_profiles 创建索引
CREATE INDEX IF NOT EXISTS idx_user_profiles_device_id ON public.user_profiles(device_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_referrer_id ON public.user_profiles(referrer_id);

-- 4. 为 usage_logs 创建索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON public.usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_feature_type ON public.usage_logs(feature_type);

-- 5. 启用行级安全策略 (RLS)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_logs ENABLE ROW LEVEL SECURITY;

-- 6. 创建 RLS 策略

-- 用户只能查看自己的资料
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

-- 用户只能更新自己的资料
CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);

-- 允许服务角色（后端）完整访问
CREATE POLICY "Service role has full access to profiles" ON public.user_profiles
    FOR ALL USING (auth.role() = 'service_role');

-- 用户只能查看自己的使用记录
CREATE POLICY "Users can view own usage logs" ON public.usage_logs
    FOR SELECT USING (auth.uid() = user_id);

-- 服务角色可以插入使用记录
CREATE POLICY "Service role can insert usage logs" ON public.usage_logs
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

-- 7. 创建自动更新 updated_at 的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 8. 为 user_profiles 添加触发器
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================================
-- 脚本执行完成！
-- ====================================================
