
export enum BodyType {
  SLIM = '苗条',
  STANDARD = '标准',
  ATHLETIC = '健壮',
  PLUMP = '丰满'
}

export type AppTab = 'clothing' | 'accessory' | 'tongue' | 'face-analysis' | 'face-reading' | 'hairstyle';

export interface User {
  nickname: string;
  deviceId: string;
  credits: number;
  referralsToday: number;
  lastReferralDate: string;
}

export interface TryOnRequest {
  faceImage: string; // base64
  itemImage: string; // base64 (clothing or earring)
  height?: number;
  bodyType?: BodyType;
  type: 'clothing' | 'accessory';
}

export interface TCMRequest {
  image: string; // base64
  type: 'tongue' | 'face-analysis' | 'face-reading';
}

export interface HairstyleRequest {
  image: string;
  gender: '男' | '女';
  age: number;
}

export interface GenerationResult {
  imageUrl?: string;
  textResult?: string;
  type: AppTab;
  extraImages?: string[]; // Used for multiple hairstyles
}
