import { z } from 'zod';

export const PartySchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid(),
  name: z.string(),
  role: z.string(),
  email: z.string(),
  phone: z.string().nullable().optional(),
  company: z.string().nullable().optional(),
  is_primary: z.boolean().default(false),
  notes: z.record(z.any()).nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Party = z.infer<typeof PartySchema>;
