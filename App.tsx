
import React, { useState, useEffect } from 'react';
import { BodyType, AppTab, User } from './types';
import ImagePicker from './components/ImagePicker';
import LoadingOverlay from './components/LoadingOverlay';
import * as api from './services/api';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'home' | 'profile'>('home');
  const [activeTab, setActiveTab] = useState<AppTab>('clothing');
  const [loading, setLoading] = useState(false);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const [extraImages, setExtraImages] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Auth States
  const [user, setUser] = useState<User | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [nicknameInput, setNicknameInput] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Form States
  const [cFace, setCFace] = useState<string | null>(null);
  const [cItem, setCItem] = useState<string | null>(null);
  const [height, setHeight] = useState<string>('165');
  const [bodyType, setBodyType] = useState<BodyType>(BodyType.STANDARD);
  const [aFace, setAFace] = useState<string | null>(null);
  const [aItem, setAItem] = useState<string | null>(null);
  const [tImage, setTImage] = useState<string | null>(null);
  const [fImage, setFImage] = useState<string | null>(null);
  const [frImage, setFrImage] = useState<string | null>(null);
  const [hFace, setHFace] = useState<string | null>(null);
  const [hGender, setHGender] = useState<'男' | '女'>('女');
  const [hAge, setHAge] = useState<string>('25');

  // 初始化：检查登录状态
  useEffect(() => {
    const initAuth = async () => {
      if (api.isAuthenticated()) {
        const profile = await api.getProfile();
        if (profile) {
          setUser({
            nickname: profile.nickname,
            deviceId: profile.device_id,
            credits: profile.credits,
            referralsToday: profile.referrals_today,
            lastReferralDate: profile.last_referral_date
          });
        }
      }
    };
    initAuth();
  }, []);

  /**
   * 处理用户登录/注册
   */
  const handleAuth = async () => {
    setAuthError(null);
    setAuthLoading(true);

    try {
      // 获取 URL 中的推荐码
      const urlParams = new URLSearchParams(window.location.search);
      const refId = urlParams.get('ref');

      if (authMode === 'register') {
        if (!usernameInput || !passwordInput || !nicknameInput) {
          setAuthError("信息不完整哦，快填好它！🍭");
          return;
        }

        const result = await api.register(
          usernameInput,
          passwordInput,
          nicknameInput,
          refId || undefined
        );

        if (result.success && result.user) {
          setUser({
            nickname: result.user.nickname,
            deviceId: result.user.device_id,
            credits: result.user.credits,
            referralsToday: result.user.referrals_today,
            lastReferralDate: result.user.last_referral_date
          });
          setShowAuth(false);
          // 清除 URL 中的 ref 参数
          window.history.replaceState({}, document.title, window.location.pathname);
          alert("✨ 注册成功！赠送你 3 次魔法值。如果有好友推荐你，TA也获得了奖励哦！");
        } else {
          setAuthError(result.message || "注册失败");
        }
      } else {
        if (!usernameInput || !passwordInput) {
          setAuthError("请输入用户名和密码");
          return;
        }

        const result = await api.login(usernameInput, passwordInput);

        if (result.success && result.user) {
          setUser({
            nickname: result.user.nickname,
            deviceId: result.user.device_id,
            credits: result.user.credits,
            referralsToday: result.user.referrals_today,
            lastReferralDate: result.user.last_referral_date
          });
          setShowAuth(false);
        } else {
          setAuthError(result.message || "登录失败");
        }
      }
    } catch (err: any) {
      setAuthError(err.message || "操作失败，请稍后重试");
    } finally {
      setAuthLoading(false);
    }
  };

  /**
   * 处理用户登出
   */
  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setCurrentView('home');
  };

  /**
   * 处理分享链接
   */
  const handleShare = () => {
    if (!user) {
      setShowAuth(true);
      return;
    }
    const shareLink = `${window.location.origin}${window.location.pathname}?ref=${user.deviceId}`;
    navigator.clipboard.writeText(shareLink);
    alert("✨ 专属邀请链接已复制！\n\n发送给好友，当TA使用新设备注册账号后，你将自动获得 1 次魔法值奖励！🎁");
  };

  /**
   * 处理 AI 功能调用
   */
  const handleGenerate = async () => {
    if (!user) {
      setShowAuth(true);
      return;
    }

    if (user.credits <= 0) {
      setError("呜呜，次数用完啦！快在个人中心分享给小伙伴获取次数吧~ 🎁");
      return;
    }

    setError(null);
    setResultImage(null);
    setResultText(null);
    setExtraImages([]);

    try {
      setLoading(true);

      if (activeTab === 'clothing') {
        if (!cFace || !cItem) throw new Error("亲，还没传照片和衣服哦！");
        const result = await api.tryOn(cFace, cItem, 'clothing', parseInt(height), bodyType);
        if (result.success && result.image) {
          setResultImage(result.image);
        } else {
          throw new Error(result.message);
        }
      } else if (activeTab === 'accessory') {
        if (!aFace || !aItem) throw new Error("快上传美照和耳饰试试吧！");
        const result = await api.tryOn(aFace, aItem, 'accessory');
        if (result.success && result.image) {
          setResultImage(result.image);
        } else {
          throw new Error(result.message);
        }
      } else if (activeTab === 'tongue') {
        if (!tImage) throw new Error("舌头照片在哪里呀？");
        const result = await api.analyze(tImage, 'tongue');
        if (result.success && result.text) {
          setResultText(result.text);
        } else {
          throw new Error(result.message);
        }
      } else if (activeTab === 'face-analysis') {
        if (!fImage) throw new Error("先拍个美美的正脸吧！");
        const result = await api.analyze(fImage, 'face-analysis');
        if (result.success && result.text) {
          setResultText(result.text);
        } else {
          throw new Error(result.message);
        }
      } else if (activeTab === 'face-reading') {
        if (!frImage) throw new Error("想看运势得先传照片哦！");
        const result = await api.analyze(frImage, 'face-reading');
        if (result.success && result.text) {
          setResultText(result.text);
        } else {
          throw new Error(result.message);
        }
      } else if (activeTab === 'hairstyle') {
        if (!hFace) throw new Error("传张正脸，我帮你选发型！");
        const result = await api.generateHairstyleRecommendation(hFace, hGender, parseInt(hAge));
        if (result.success) {
          setResultText(result.analysis || null);
          setResultImage(result.recommended_image || null);
          if (result.catalog_image) {
            setExtraImages([result.catalog_image]);
          }
        } else {
          throw new Error(result.message);
        }
      }

      // 更新本地用户状态（魔法值已在后端扣减）
      setUser(prev => prev ? { ...prev, credits: prev.credits - 1 } : null);

    } catch (err: any) {
      setError(err.message || "哎呀，服务器开小差了，再试一次吧！");
    } finally {
      setLoading(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const reset = () => {
    setResultImage(null);
    setResultText(null);
    setExtraImages([]);
    setError(null);
  };

  const NavCard = ({ id, label, icon, bgColor }: { id: AppTab, label: string, icon: React.ReactNode, bgColor: string }) => (
    <button
      onClick={() => { setActiveTab(id); reset(); }}
      className={`flex flex-col items-center justify-center p-4 rounded-3xl bouncy relative overflow-hidden transition-all ${activeTab === id ? `${bgColor} text-white shadow-xl scale-105` : 'bg-white text-gray-400 opacity-80'
        }`}
    >
      <div className={`mb-2 ${activeTab === id ? 'animate-bounce' : ''}`}>{icon}</div>
      <span className="text-xs font-bold tracking-wider">{label}</span>
      {activeTab === id && <div className="absolute top-1 right-1 w-2 h-2 bg-white rounded-full"></div>}
    </button>
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#fdfcfb]">
      {loading && <LoadingOverlay message="魔法生成中，请稍等哦 ✨" />}

      {/* Auth Modal */}
      {showAuth && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-6 overflow-y-auto">
          <div className="glass-card w-full max-w-sm p-8 rounded-[3rem] text-center space-y-6 animate-in zoom-in duration-300 relative">
            <button onClick={() => { setShowAuth(false); setAuthError(null); }} className="absolute top-6 right-6 text-gray-300">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            <div className="w-16 h-16 bg-pink-400 rounded-full flex items-center justify-center text-3xl mx-auto shadow-lg">🍭</div>
            <div>
              <h2 className="text-2xl font-happy text-pink-500">{authMode === 'login' ? '欢迎回来！' : '加入魔法之旅'}</h2>
              <p className="text-[10px] text-gray-400 mt-2 font-bold uppercase tracking-widest">请登录您的魔法账号</p>
            </div>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="用户名..."
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border-2 border-gray-100 focus:border-pink-300 outline-none text-center font-bold text-gray-700"
              />
              <input
                type="password"
                placeholder="密码..."
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border-2 border-gray-100 focus:border-pink-300 outline-none text-center font-bold text-gray-700"
              />
              {authMode === 'register' && (
                <input
                  type="text"
                  placeholder="昵称 (如: 甜心超人)..."
                  value={nicknameInput}
                  onChange={(e) => setNicknameInput(e.target.value)}
                  className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border-2 border-gray-100 focus:border-pink-300 outline-none text-center font-bold text-gray-700 animate-in slide-in-from-top-2"
                />
              )}
            </div>

            {authError && <p className="text-[10px] font-bold text-red-400 animate-pulse">{authError}</p>}

            <button
              onClick={handleAuth}
              disabled={authLoading}
              className="w-full candy-button py-4 font-bold bouncy text-lg disabled:opacity-50"
            >
              {authLoading ? '处理中...' : (authMode === 'login' ? '立即登录 ✨' : '完成注册 🎁')}
            </button>

            <button
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'register' : 'login');
                setAuthError(null);
              }}
              className="text-[10px] font-bold text-gray-400 hover:text-pink-500 transition-colors uppercase tracking-widest"
            >
              {authMode === 'login' ? '还没有账号？去注册' : '已有账号？去登录'}
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="px-6 pt-8 pb-4 flex items-center justify-center safe-top sticky top-0 bg-[#fdfcfb]/80 backdrop-blur-md z-40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 candy-button flex items-center justify-center text-white text-xl rotate-3 shadow-lg">✨</div>
          <h1 className="text-2xl font-happy text-[#FF7E67] tracking-tight">魅丽变变变</h1>
        </div>
      </header>

      <main className="flex-1 max-w-md mx-auto w-full px-5 pb-32">
        {currentView === 'home' ? (
          (resultImage || resultText) ? (
            <div className="space-y-6 animate-in fade-in zoom-in duration-500 py-4">
              <div className="glass-card rounded-[2.5rem] p-3">
                {resultImage && (
                  <img src={resultImage} alt="Magic Result" className="w-full h-auto rounded-[2rem] shadow-inner" />
                )}
              </div>
              {extraImages.map((img, idx) => (
                <div key={idx} className="glass-card rounded-[2.5rem] p-3">
                  <img src={img} alt={`Extra ${idx}`} className="w-full h-auto rounded-[2rem]" />
                </div>
              ))}
              {resultText && (
                <div className="glass-card p-8 rounded-[2.5rem] relative">
                  <div className="absolute -top-4 -left-4 w-12 h-12 bg-purple-400 rounded-full flex items-center justify-center text-white text-xl shadow-lg">💡</div>
                  <h2 className="text-xl font-happy text-purple-600 mb-4">魔法建议报告</h2>
                  <div className="text-gray-600 whitespace-pre-wrap leading-relaxed text-sm font-medium">{resultText}</div>
                </div>
              )}
              <button onClick={reset} className="w-full candy-button py-5 text-lg font-bold flex items-center justify-center gap-3 bouncy">再变一次！✨</button>
            </div>
          ) : (
            <div className="space-y-8 py-4">
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-gray-400 ml-2">🎀 时尚造型馆</h3>
                <div className="grid grid-cols-3 gap-3">
                  <NavCard id="clothing" label="云试衣" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>} bgColor="bg-[#FF7E67]" />
                  <NavCard id="accessory" label="戴耳饰" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 1.343-3 3v4a3 3 0 106 0v-4c0-1.657-1.343-3-3-3z" /></svg>} bgColor="bg-[#FF9A8B]" />
                  <NavCard id="hairstyle" label="美发型" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758L5 19m0-14l4.121 4.121" /></svg>} bgColor="bg-[#A594F9]" />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-sm font-bold text-gray-400 ml-2">🍵 传统文化智慧</h3>
                <div className="grid grid-cols-3 gap-3">
                  <NavCard id="tongue" label="舌象" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} bgColor="bg-[#6DE3B7]" />
                  <NavCard id="face-analysis" label="面色" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} bgColor="bg-[#FFE66D] !text-gray-700" />
                  <NavCard id="face-reading" label="面相" icon={<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A10.003 10.003 0 0012 3c1.708 0 3.28.427 4.65 1.173a10.003 10.003 0 014.593 8.39c0 5.523-4.477 10-10 10a9.96 9.96 0 01-4.593-1.11z" /></svg>} bgColor="bg-pink-400" />
                </div>
              </div>

              <div className="space-y-6 animate-in fade-in duration-500">
                {activeTab === 'clothing' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <ImagePicker label="拍张帅照/美照" value={cFace} onChange={setCFace} icon={<span className="text-3xl">👤</span>} />
                      <ImagePicker label="这衣服真好看" value={cItem} onChange={setCItem} icon={<span className="text-3xl">👗</span>} />
                    </div>
                    <div className="glass-card p-6 rounded-[2rem] space-y-6">
                      <div className="flex justify-between items-center px-1">
                        <label className="text-xs font-bold text-gray-500">你是多高呢？</label>
                        <span className="text-xl font-happy text-[#FF7E67]">{height}cm</span>
                      </div>
                      <input type="range" min="140" max="210" value={height} onChange={(e) => setHeight(e.target.value)} className="w-full" />
                      <div className="grid grid-cols-2 gap-2">
                        {Object.values(BodyType).map((type) => (
                          <button key={type} onClick={() => setBodyType(type)} className={`py-3 rounded-2xl text-xs font-bold bouncy ${bodyType === type ? 'bg-[#FF7E67] text-white shadow-md' : 'bg-gray-100 text-gray-400'}`}>{type}</button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                {activeTab === 'accessory' && (
                  <div className="grid grid-cols-2 gap-4">
                    <ImagePicker label="上传头像" value={aFace} onChange={setAFace} icon={<span className="text-3xl">🤳</span>} />
                    <ImagePicker label="耳饰照片" value={aItem} onChange={setAItem} icon={<span className="text-3xl">💎</span>} />
                  </div>
                )}
                {activeTab === 'hairstyle' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <ImagePicker label="上传正脸" value={hFace} onChange={setHFace} icon={<span className="text-3xl">📸</span>} />
                      <div className="flex flex-col gap-4">
                        <div className="space-y-2">
                          <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-1">性别</label>
                          <div className="grid grid-cols-2 gap-1.5">
                            <button onClick={() => setHGender('男')} className={`py-3 rounded-xl border-2 transition-all text-xs font-bold ${hGender === '男' ? 'border-[#A594F9] bg-[#A594F9] text-white shadow-md' : 'border-gray-100 text-gray-400 bg-white'}`}>男生</button>
                            <button onClick={() => setHGender('女')} className={`py-3 rounded-xl border-2 transition-all text-xs font-bold ${hGender === '女' ? 'border-[#A594F9] bg-[#A594F9] text-white shadow-md' : 'border-gray-100 text-gray-400 bg-white'}`}>女生</button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between items-center px-1">
                            <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">年龄</label>
                            <span className="text-sm font-happy text-[#A594F9]">{hAge}岁</span>
                          </div>
                          <input type="range" min="5" max="80" value={hAge} onChange={(e) => setHAge(e.target.value)} className="w-full h-1 bg-gray-200 accent-[#A594F9]" />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {activeTab === 'face-reading' && (
                  <ImagePicker
                    label="上传正面照看运势"
                    value={frImage}
                    onChange={setFrImage}
                    icon={<span className="text-4xl">🔮</span>}
                    layout="horizontal"
                  />
                )}
                {(activeTab === 'tongue' || activeTab === 'face-analysis') && (
                  <ImagePicker
                    label={activeTab === 'tongue' ? "把舌头伸出来呀" : "拍张清晰的正脸"}
                    value={activeTab === 'tongue' ? tImage : fImage}
                    onChange={activeTab === 'tongue' ? setTImage : setFImage}
                    icon={<span className="text-4xl">{activeTab === 'tongue' ? '👅' : '💆'}</span>}
                    layout="horizontal"
                  />
                )}
              </div>
              {error && <div className="p-4 bg-red-100 text-red-500 text-xs font-bold rounded-2xl text-center animate-bounce">{error}</div>}
              <button onClick={handleGenerate} className="candy-button w-full py-5 text-xl font-happy shadow-xl bouncy disabled:opacity-50" disabled={loading}>立刻开启魔法分析 ✨</button>
            </div>
          )
        ) : (
          <div className="py-8 animate-in slide-in-from-bottom-5 duration-500">
            {user ? (
              <div className="space-y-8">
                <div className="text-center space-y-4">
                  <div className="relative inline-block">
                    <div className="w-24 h-24 bg-[#6DE3B7] rounded-full flex items-center justify-center text-5xl mx-auto shadow-lg border-4 border-white">✨</div>
                    <button onClick={handleLogout} className="absolute -bottom-2 -right-2 bg-red-400 text-white p-2 rounded-full shadow-md hover:bg-red-500 transition-colors bouncy">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                    </button>
                  </div>
                  <div>
                    <h2 className="text-2xl font-happy text-gray-700">{user.nickname}</h2>
                    <div className="mt-1 inline-block px-3 py-1 bg-gray-100 rounded-full text-[10px] font-bold text-gray-400 uppercase tracking-widest">本机 ID: ...{user.deviceId.slice(-6)}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  <div className="glass-card p-8 rounded-[2.5rem] text-center border-pink-100">
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">剩余魔法次数</p>
                    <div className="text-6xl font-happy text-pink-500">{user.credits}</div>
                  </div>

                  <div className="glass-card p-8 rounded-[2.5rem] space-y-6">
                    <div className="text-center space-y-2">
                      <h3 className="text-lg font-happy text-purple-500">魔法补给站 🎁</h3>
                      <p className="text-[11px] font-bold text-gray-400 leading-relaxed px-4">
                        分享链接给不同设备的好友注册<br />
                        每成功 1 人赠送 1 次<br />
                        <span className="text-pink-400 opacity-60">(今日已领: {user.referralsToday}/5)</span>
                      </p>
                    </div>
                    <button onClick={handleShare} className="w-full candy-button py-5 font-bold bouncy flex items-center justify-center gap-3 text-lg">
                      <span>🚀</span> 立即分享链接
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-20 space-y-6">
                <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center text-4xl mx-auto text-gray-300">🔒</div>
                <div className="space-y-2">
                  <h2 className="text-xl font-happy text-gray-400">尚未登录哦</h2>
                  <p className="text-xs text-gray-300 font-bold uppercase">快去首页开启你的第一次魔法吧！</p>
                </div>
                <button onClick={() => { setShowAuth(true); setAuthMode('login'); }} className="candy-button px-8 py-4 font-bold bouncy">去登录 / 注册</button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 px-6 pb-8 pt-4 safe-bottom">
        <div className="max-w-md mx-auto glass-card rounded-[3rem] p-2 flex items-center shadow-2xl border-white/80">
          <button
            onClick={() => setCurrentView('home')}
            className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-[2.5rem] transition-all bouncy ${currentView === 'home' ? 'bg-[#FF7E67] text-white shadow-lg' : 'text-gray-400 hover:text-[#FF7E67]'
              }`}
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" /></svg>
            <span className="text-[10px] font-bold uppercase tracking-widest">魔法首页</span>
          </button>

          <button
            onClick={() => {
              if (!user) { setShowAuth(true); setAuthMode('login'); return; }
              setCurrentView('profile');
            }}
            className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-[2.5rem] transition-all bouncy relative ${currentView === 'profile' ? 'bg-[#A594F9] text-white shadow-lg' : 'text-gray-400 hover:text-[#A594F9]'
              }`}
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg>
            <span className="text-[10px] font-bold uppercase tracking-widest">个人中心</span>
            {user && user.credits > 0 && currentView !== 'profile' && (
              <div className="absolute top-2 right-1/3 w-3 h-3 bg-red-400 rounded-full border-2 border-white animate-pulse"></div>
            )}
          </button>
        </div>
      </nav>

      <footer className="mt-auto px-10 py-6 text-center opacity-30 pb-32">
        <p className="text-[10px] text-gray-500 font-bold uppercase tracking-[0.2em]">Happy Beauty Magic Lab<br />© 2025 魅丽变变变</p>
      </footer>
    </div>
  );
};

export default App;
