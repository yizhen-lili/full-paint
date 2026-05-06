// Zod schemas — 對應 backend/auth/schemas/request.py 規則
import { z } from 'zod'

// 密碼：≥10 字元 + 含英文字母 + 含數字
export const passwordSchema = z
  .string()
  .min(10, '密碼至少需要 10 個字元')
  .regex(/[A-Za-z]/, '密碼需包含英文字母')
  .regex(/\d/, '密碼需包含數字')

export const emailSchema = z.string().email('email 格式不正確')

export const registerSchema = z.object({
  name: z.string().min(4, '名稱至少需要 4 個字元'),
  email: emailSchema,
  password: passwordSchema,
})

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, '請輸入密碼'),
})

export const forgotPasswordSchema = z.object({
  email: emailSchema,
})

export const resetPasswordSchema = z.object({
  new_password: passwordSchema,
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: '兩次輸入的密碼不一致',
  path: ['confirm_password'],
})

export type RegisterValues = z.infer<typeof registerSchema>
export type LoginValues = z.infer<typeof loginSchema>
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>
