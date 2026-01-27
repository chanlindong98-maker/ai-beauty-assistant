
import React from 'react';

const LoadingOverlay: React.FC<{ message?: string }> = ({ message = "魔法正在发生..." }) => {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/90 backdrop-blur-md px-10 text-center">
      <div className="flex space-x-2 mb-8">
        <div className="w-4 h-4 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
        <div className="w-4 h-4 bg-[#FFE66D] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
        <div className="w-4 h-4 bg-[#6DE3B7] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-4 h-4 bg-[#A594F9] rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
      </div>
      
      <div className="space-y-4">
        <h2 className="text-2xl font-happy text-pink-500 tracking-wide animate-pulse">{message}</h2>
        <div className="flex flex-col items-center opacity-30">
           <p className="text-[10px] font-bold uppercase tracking-[0.4em]">Beauty Magic in Progress</p>
           <div className="w-24 h-1 bg-gray-100 rounded-full mt-2 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-pink-400 to-purple-400 w-1/2 animate-[shimmer_1.5s_infinite]"></div>
           </div>
        </div>
      </div>
      
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
      `}</style>
    </div>
  );
};

export default LoadingOverlay;
