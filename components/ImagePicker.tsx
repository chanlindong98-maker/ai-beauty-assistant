
import React, { useRef } from 'react';

interface ImagePickerProps {
  label: string;
  value: string | null;
  onChange: (base64: string) => void;
  icon: React.ReactNode;
  layout?: 'vertical' | 'horizontal';
}

const ImagePicker: React.FC<ImagePickerProps> = ({ label, value, onChange, icon, layout = 'vertical' }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        onChange(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const isHorizontal = layout === 'horizontal';

  return (
    <div className={`flex flex-col space-y-2 ${isHorizontal ? 'w-full' : 'flex-1 min-w-0'}`}>
      <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-2">{label}</label>
      
      <div className={`flex ${isHorizontal ? 'flex-row items-center gap-6' : 'flex-col'}`}>
        <div 
          onClick={() => inputRef.current?.click()}
          className={`relative rounded-[2.5rem] border-4 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-300 overflow-hidden group bouncy ${
            value 
            ? 'border-[#FFE66D] bg-white' 
            : 'border-gray-200 bg-white hover:border-pink-300'
          } ${isHorizontal ? 'w-32 h-32 shrink-0' : 'aspect-[1/1] w-full'}`}
        >
          {value ? (
            <>
              <img src={value} alt="Preview" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-white/40 flex items-center justify-center opacity-0 group-active:opacity-100 transition-opacity">
                 <div className="p-3 bg-white rounded-full shadow-lg text-pink-500">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center space-y-2 text-gray-300 p-4 text-center">
              <div className="group-hover:scale-125 transition-transform duration-500">
                {icon}
              </div>
              <span className="text-[10px] font-bold uppercase tracking-widest">点我上传</span>
            </div>
          )}
          <input 
            type="file" 
            ref={inputRef}
            onChange={handleFileChange}
            accept="image/*"
            className="hidden"
          />
        </div>

        <p className={`text-[10px] text-gray-400 font-medium leading-relaxed ${isHorizontal ? 'flex-1 text-left' : 'text-center mt-1 px-1'}`}>
          本应用没有数据库，上传的图片测完即删，不会存档，请放心使用
        </p>
      </div>
    </div>
  );
};

export default ImagePicker;
