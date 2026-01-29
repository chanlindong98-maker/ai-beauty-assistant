import React, { useState, useEffect } from 'react';
import * as api from '../services/api';

interface AdminDashboardProps {
    onClose: () => void;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ onClose }) => {
    const [stats, setStats] = useState<api.DashboardStats | null>(null);
    const [users, setUsers] = useState<api.AdminUserDetail[]>([]);
    const [config, setConfig] = useState<api.SystemConfigItem[]>([]);
    const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'config' | 'security'>('stats');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [showKeys, setShowKeys] = useState<{ [key: string]: boolean }>({});

    useEffect(() => {
        loadData();
    }, [activeTab]);

    const loadData = async () => {
        setLoading(true);
        try {
            setError(null);
            if (activeTab === 'stats') {
                const s = await api.getAdminStats();
                setStats(s);
            } else if (activeTab === 'users') {
                const u = await api.getAdminUsers(searchQuery);
                setUsers(u);
            } else if (activeTab === 'config') {
                const c = await api.getAdminConfig();
                setConfig(c);
            }
        } catch (err) {
            console.error('Admin Load Error:', err);
            setError((err as Error).message || '数据加载失败，请检查数据库配置');
        } finally {
            setLoading(false);
        }
    };

    const handleAdjustCredits = async (userId: string) => {
        const val = prompt('请输入增加的魔法次数 (输入负数进行扣除):', '10');
        if (val === null) return;
        const num = parseInt(val);
        if (isNaN(num)) return;

        try {
            await api.updateAdminUserCredits(userId, num, 'add');
            loadData();
        } catch (err) {
            alert('操作失败: ' + (err as Error).message);
        }
    };

    const handleSaveConfig = async () => {
        try {
            await api.updateAdminConfig(config);
            alert('系统设置已保存并立即生效');
        } catch (err) {
            alert('保存失败: ' + (err as Error).message);
        }
    };

    const handleConfigChange = (key: string, value: string) => {
        setConfig(prev => prev.map(item => item.key === key ? { ...item, value } : item));
    };

    const toggleKeyVisibility = (key: string) => {
        setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const handleChangePassword = async () => {
        const pwd = prompt('设置新的管理员登录密码 (至少8位):');
        if (!pwd) return;
        if (pwd.length < 8) {
            alert('为了安全，密码长度不能少于 8 位');
            return;
        }
        try {
            await api.resetAdminPassword(pwd);
            alert('密码已成功更新，下次请使用新密码登录');
        } catch (err) {
            alert('修改失败: ' + (err as Error).message);
        }
    };

    // 格式化金额
    const formatCNY = (amount: number) => {
        return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(amount);
    };

    return (
        <div className="fixed inset-0 z-[100] flex bg-gray-50 text-slate-800 font-sans antialiased overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 bg-slate-900 flex flex-col shrink-0 border-r border-slate-800 shadow-2xl">
                <div className="p-8">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 19V5l12-2v14L9 19zm0 0l4-2M9 5l4-2" /></svg>
                        </div>
                        <div>
                            <h1 className="text-white font-bold text-lg leading-tight">魅丽运营</h1>
                            <p className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Management Console</p>
                        </div>
                    </div>
                </div>

                <nav className="flex-1 px-4 space-y-1">
                    {[
                        { id: 'stats' as const, label: '数据分析', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
                        { id: 'users' as const, label: '会员管理', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' },
                        { id: 'config' as const, label: '参数配置', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
                        { id: 'security' as const, label: '安全中心', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 ${activeTab === tab.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                        >
                            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={tab.icon} /></svg>
                            {tab.label}
                        </button>
                    ))}
                </nav>

                <div className="p-4 mt-auto">
                    <button
                        onClick={onClose}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-slate-700 font-bold text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all uppercase tracking-widest"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7" /></svg>
                        返回主应用
                    </button>
                </div>
            </aside>

            {/* Main Area */}
            <main className="flex-1 flex flex-col min-w-0">
                {/* Top Header */}
                <header className="h-20 bg-white border-b border-gray-200 px-10 flex items-center justify-between shadow-sm shrink-0">
                    <div className="flex flex-col">
                        <h2 className="text-xl font-bold text-slate-900">{
                            activeTab === 'stats' ? '营收数据统计' :
                                activeTab === 'users' ? '平台会员管理' :
                                    activeTab === 'config' ? '系统核心参数配置' : '运营安全中心'
                        }</h2>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Real-time control panel</p>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="text-right">
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">系统健康度</p>
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                <span className="text-sm font-bold text-slate-700">Service Online</span>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-10">
                    {loading && (
                        <div className="flex flex-col items-center justify-center h-full gap-4 text-indigo-500">
                            <svg className="w-10 h-10 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle className="opacity-25" cx="12" cy="12" r="10" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                            <span className="font-bold text-slate-400 uppercase tracking-widest text-xs">正在调取云端数据...</span>
                        </div>
                    )}

                    {error && (
                        <div className="bg-rose-50 border border-rose-100 rounded-2xl p-8 text-center animate-in fade-in zoom-in duration-300">
                            <div className="w-16 h-16 bg-rose-100 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                            </div>
                            <h3 className="text-lg font-bold text-slate-800 mb-2">数据加载异常</h3>
                            <p className="text-sm text-slate-500 mb-6">{error}</p>
                            {error.includes('orders') && (
                                <p className="text-xs text-indigo-500 font-bold mb-6">提示：这通常是因为数据库缺少 orders 表，请在数据库运行补全脚本。</p>
                            )}
                            <button onClick={loadData} className="px-6 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-black transition-all">重试加载</button>
                        </div>
                    )}

                    {!loading && !error && activeTab === 'stats' && stats && (
                        <div className="space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                                {[
                                    { label: '累计流水', value: formatCNY(stats.total_recharge_amount), trend: '+12.5%', color: 'from-blue-500 to-indigo-600' },
                                    { label: '今日新增', value: formatCNY(stats.today_recharge_amount), trend: '+8.2%', color: 'from-emerald-500 to-teal-600' },
                                    { label: '注册规模', value: stats.total_users, trend: '+5.4%', color: 'from-violet-500 to-purple-600' },
                                    { label: '交易笔数', value: stats.total_orders, trend: '+10.1%', color: 'from-amber-500 to-orange-600' },
                                ].map((card, i) => (
                                    <div key={i} className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-xl hover:shadow-indigo-500/5 transition-all">
                                        <div className="flex justify-between items-start mb-6">
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{card.label}</p>
                                            <span className="px-2 py-0.5 bg-gray-50 text-[10px] font-bold text-emerald-500 rounded-lg">{card.trend}</span>
                                        </div>
                                        <p className="text-3xl font-black text-slate-900 tracking-tight">{card.value}</p>
                                        <div className="mt-6 w-full h-1.5 bg-gray-50 rounded-full overflow-hidden">
                                            <div className={`h-full bg-gradient-to-r ${card.color} rounded-full`} style={{ width: '70%' }}></div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="bg-white rounded-3xl p-10 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="font-bold text-slate-800">实时经营趋势</h3>
                                    <select className="bg-gray-50 border-none rounded-xl text-xs font-bold px-4 py-2 text-slate-500 outline-none">
                                        <option>最近 7 天</option>
                                        <option>最近 30 天</option>
                                    </select>
                                </div>
                                <div className="h-64 flex items-end justify-between gap-4 px-2">
                                    {[40, 60, 45, 90, 65, 80, 50].map((h, i) => (
                                        <div key={i} className="flex-1 group relative">
                                            <div className="w-full bg-indigo-50 group-hover:bg-indigo-500 transition-all rounded-xl relative overflow-hidden" style={{ height: `${h}%` }}>
                                                <div className="absolute inset-0 bg-gradient-to-t from-black/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                            </div>
                                            <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                                                {h * 10}笔
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex justify-between mt-6 px-2">
                                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
                                        <span key={day} className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{day}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {!loading && !error && activeTab === 'users' && (
                        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <div className="flex items-center justify-between">
                                <div className="relative group flex-1 max-w-md">
                                    <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                                    <input
                                        type="text"
                                        placeholder="搜索用户昵称或设备 ID..."
                                        className="w-full pl-12 pr-6 py-4 rounded-2xl bg-white border border-gray-100 shadow-sm outline-none focus:border-indigo-500 transition-all text-sm"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && loadData()}
                                    />
                                </div>
                                <button onClick={loadData} className="px-8 py-4 bg-indigo-600 text-white rounded-2xl shadow-xl shadow-indigo-600/20 font-bold text-sm hover:translate-y-[-2px] active:translate-y-0 transition-all">筛选记录</button>
                            </div>

                            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left border-collapse">
                                        <thead>
                                            <tr className="border-b border-gray-50 bg-slate-50/50">
                                                <th className="px-10 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">用户信息</th>
                                                <th className="px-10 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-center">魔法值</th>
                                                <th className="px-10 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">身份标签</th>
                                                <th className="px-10 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">后台操作</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-50">
                                            {users.map(u => (
                                                <tr key={u.id} className="group hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-10 py-6">
                                                        <div className="flex items-center gap-4">
                                                            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 font-bold text-sm">{u.nickname.charAt(0)}</div>
                                                            <div>
                                                                <div className="font-bold text-slate-800">{u.nickname}</div>
                                                                <div className="text-[10px] text-slate-400 font-mono mt-0.5">{u.id}</div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-10 py-6 text-center">
                                                        <span className="inline-block px-4 py-1.5 bg-indigo-50 text-indigo-600 rounded-xl font-bold text-sm tracking-tight">{u.credits}次</span>
                                                    </td>
                                                    <td className="px-10 py-6">
                                                        {u.is_admin ? (
                                                            <span className="px-3 py-1 bg-slate-900 text-white text-[9px] font-bold rounded-full uppercase tracking-widest">Administrator</span>
                                                        ) : (
                                                            <span className="px-3 py-1 bg-gray-100 text-gray-500 text-[9px] font-bold rounded-full uppercase tracking-widest">Member</span>
                                                        )}
                                                    </td>
                                                    <td className="px-10 py-6 text-right">
                                                        <button
                                                            onClick={() => handleAdjustCredits(u.id)}
                                                            className="px-4 py-2 bg-white border border-gray-200 text-slate-600 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:border-indigo-500 hover:text-indigo-600 transition-all shadow-sm"
                                                        >
                                                            增减额度
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {users.length === 0 && (
                                                <tr>
                                                    <td colSpan={4} className="py-20 text-center text-slate-400 font-bold text-xs uppercase tracking-[0.2em]">未检索到相关会员数据</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {!loading && !error && activeTab === 'config' && (
                        <div className="space-y-10 max-w-4xl animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <h3 className="font-bold text-slate-800 text-lg">系统核心参数配置</h3>
                                    <p className="text-xs text-slate-400 font-medium">包含支付接口与 AI 引擎配置，修改后立即生效</p>
                                </div>
                                <button onClick={handleSaveConfig} className="px-10 py-4 bg-emerald-500 text-white rounded-2xl shadow-xl shadow-emerald-500/20 font-black text-sm hover:translate-y-[-2px] transition-all uppercase tracking-widest">发布配置</button>
                            </div>

                            <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100 grid grid-cols-1 md:grid-cols-2 gap-8">
                                {config.map(item => (
                                    <div key={item.key} className={`space-y-3 ${item.key.includes('key') ? 'md:col-span-2' : ''}`}>
                                        <div className="flex items-center justify-between px-1">
                                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                                <span className="w-1 h-3 bg-indigo-500 rounded-full"></span>
                                                {item.description || item.key}
                                            </label>
                                            {item.key.includes('key') && (
                                                <button onClick={() => toggleKeyVisibility(item.key)} className="text-[9px] font-bold text-indigo-500 uppercase tracking-widest hover:underline">
                                                    {showKeys[item.key] ? '隐藏密钥' : '显示明文'}
                                                </button>
                                            )}
                                        </div>
                                        {item.key.includes('key') ? (
                                            <div className="relative">
                                                <textarea
                                                    value={item.value}
                                                    onChange={(e) => handleConfigChange(item.key, e.target.value)}
                                                    className={`w-full px-6 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 outline-none text-xs font-mono transition-all h-32 ${!showKeys[item.key] ? 'blur-[3px] select-none pointer-events-none opacity-40' : ''}`}
                                                    placeholder="请输入密钥内容..."
                                                />
                                                {!showKeys[item.key] && (
                                                    <div className="absolute inset-0 flex items-center justify-center">
                                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">密钥已隐藏，点击上方显示</span>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <input
                                                type="text"
                                                value={item.value}
                                                onChange={(e) => handleConfigChange(item.key, e.target.value)}
                                                className="w-full px-6 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-indigo-500 outline-none text-sm font-bold text-slate-700 transition-all font-mono"
                                                placeholder="请输入配置值..."
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {!loading && !error && activeTab === 'security' && (
                        <div className="space-y-10 max-w-xl animate-in fade-in slide-in-from-bottom-2 duration-500">
                            <div className="space-y-1">
                                <h3 className="font-bold text-slate-800 text-lg">系统权限设置</h3>
                                <p className="text-xs text-slate-400 font-medium">配置管理员个人账户的安全选项</p>
                            </div>

                            <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-gray-100 text-center space-y-8">
                                <div className="w-20 h-20 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center text-3xl mx-auto shadow-inner shadow-rose-500/10">
                                    <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                                </div>
                                <div className="space-y-2">
                                    <h4 className="font-bold text-slate-800">修改登录密码</h4>
                                    <p className="text-xs text-slate-400 leading-relaxed font-medium">定期更换密码可以显著提高系统的运营安全性。<br />新密码生效后，您无需重新登录，系统已同步更新凭证。</p>
                                </div>
                                <div className="pt-4 px-4">
                                    <button
                                        onClick={handleChangePassword}
                                        className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-sm hover:bg-black transition-all shadow-xl shadow-slate-900/10 uppercase tracking-[0.2em]"
                                    >
                                        立即重置管理员密码
                                    </button>
                                </div>
                                <div className="bg-slate-50 p-4 rounded-2xl flex items-center gap-4 text-left">
                                    <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    <p className="text-[10px] text-slate-500 font-bold leading-tight">安全提示：请务必妥善保管您的新密码。如果遗失，可能需要联系数据库管理员进行手动重置。</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

export default AdminDashboard;
